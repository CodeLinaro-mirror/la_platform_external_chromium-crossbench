# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import datetime as dt
import shutil
import struct
import subprocess
import tempfile
import unittest
import unittest.mock as mock

from crossbench import path as pth
from crossbench import plt
from crossbench.helper import wait
from crossbench.plt.bin import Binaries
from crossbench.plt.display_info import DisplayResolution
from crossbench.plt.ios import IOSPlatform
from crossbench.probes.probe_error import ProbeIncompatibleBrowser
from crossbench.probes.video import Orientation, VideoProbe, VideoProbeContext
from tests import test_helper


def _has_swift_toolchain() -> bool:
  # The recorder needs AVFoundation, and stock macOS ships /usr/bin/swiftc as
  # a shim that only works once a toolchain is installed.
  if not plt.PLATFORM.is_macos:
    return False
  try:
    plt.PLATFORM.sh("swiftc", "--version", quiet=True)
  except plt.SubprocessError:
    return False
  return True


class VideoProbeTestCase(unittest.TestCase):
  def test_default(self):
    probe = VideoProbe.parse_dict({})
    self.assertEqual(probe.primary_orientation, Orientation.HORIZONTAL)
    self.assertEqual(probe.secondary_orientation, Orientation.VERTICAL)

  def test_from_config(self):
    probe = VideoProbe.parse_dict({"orientation": "vertical"})
    self.assertEqual(probe.primary_orientation, Orientation.VERTICAL)
    self.assertEqual(probe.secondary_orientation, Orientation.HORIZONTAL)

    probe = VideoProbe.parse_dict({"dir": "horizontal"})
    self.assertEqual(probe.primary_orientation, Orientation.HORIZONTAL)
    self.assertEqual(probe.secondary_orientation, Orientation.VERTICAL)

  def test_recording_options_from_config(self):
    probe = VideoProbe.parse_dict(
      {
        "generate_timestrip": False,
        "merge_runs": False,
        "max_height": 480,
        "bitrate": 1_000_000,
        "time_limit": 0,
        "codec": "c2.android.avc.encoder",
      }
    )
    self.assertFalse(probe.generate_timestrip)
    self.assertFalse(probe.merge_runs)
    self.assertEqual(probe.max_height, 480)
    self.assertEqual(probe.bit_rate, 1_000_000)
    self.assertEqual(probe.time_limit, 0)
    self.assertEqual(probe.codec_name, "c2.android.avc.encoder")

    for invalid_config in (
      {"max_height": 0},
      {"bit_rate": 0},
      {"time_limit": -1},
      {"codec_name": ""},
    ):
      with self.assertRaises(ValueError):
        VideoProbe.parse_dict(invalid_config)

  def test_validate_env_ffmpeg_requirement_on_android(self):
    android_browser = mock.MagicMock()
    android_browser.platform.is_linux = False
    android_browser.platform.is_ios = False
    android_browser.platform.is_android = True
    android_browser.viewport.is_headless = False
    env = mock.MagicMock(repetitions=1, browsers=[android_browser])

    probe_no_ffmpeg = VideoProbe.parse_dict(
      {"generate_timestrip": False, "merge_runs": False}
    )
    probe_no_ffmpeg.attach(android_browser)
    probe_no_ffmpeg.validate_env(env)
    env.check_installed.assert_not_called()
    env.check_sh_success.assert_not_called()

    probe_timestrip = VideoProbe.parse_dict(
      {"generate_timestrip": True, "merge_runs": False}
    )
    probe_timestrip.attach(android_browser)
    probe_timestrip.validate_env(env)
    env.check_installed.assert_any_call(
      binaries=(Binaries.FFMPEG,),
      message="Missing binaries for video probe: {}",
    )

  def test_validate_env_ffmpeg_requirement_on_remote_linux(self):
    remote_linux_browser = mock.MagicMock()
    remote_linux_browser.platform.is_linux = True
    remote_linux_browser.platform.is_local = False
    remote_linux_browser.platform.is_remote = True
    remote_linux_browser.platform.is_ios = False
    remote_linux_browser.platform.is_android = False
    remote_linux_browser.viewport.is_headless = False
    remote_linux_browser.viewport.has_size = True
    remote_linux_browser.viewport.x = 100
    remote_linux_browser.viewport.y = 100
    env = mock.MagicMock(repetitions=1, browsers=[remote_linux_browser])

    probe = VideoProbe.parse_dict(
      {"generate_timestrip": False, "merge_runs": False}
    )
    probe.attach(remote_linux_browser)
    probe.validate_env(env)
    env.check_installed.assert_called_once_with(
      binaries=(Binaries.FFMPEG,),
      message="Missing binaries for video probe: {}",
      platform=remote_linux_browser.platform,
    )
    env.check_sh_success.assert_not_called()

  def test_ios_usb_recorder_source_exists(self):
    self.assertTrue(VideoProbe.IOS_USB_RECORDER_SOURCE.is_file())

  def test_validate_browser_rejects_simulators(self):
    probe = VideoProbe.parse_dict({})
    browser = mock.MagicMock()
    browser.platform = mock.MagicMock(spec=IOSPlatform, is_simulator=False)
    probe.attach(browser)
    probe.validate_browser(mock.MagicMock(), browser)
    browser.platform.is_simulator = True
    with self.assertRaises(ProbeIncompatibleBrowser):
      probe.validate_browser(mock.MagicMock(), browser)

  def test_setup_compiles_recorder_for_ios(self):
    probe = VideoProbe.parse_dict({})
    runner = mock.MagicMock()
    runner.out_dir = pth.LocalPath("/out")
    browser = mock.MagicMock()
    browser.platform.is_ios = False
    probe.attach(browser)
    probe.setup(runner)
    runner.platform.sh.assert_not_called()
    with self.assertRaises(AssertionError):
      _ = probe.ios_usb_recorder

    browser.platform.is_ios = True
    probe.setup(runner)
    binary = pth.LocalPath("/out/ios_usb_screen_recorder")
    runner.platform.sh.assert_called_once_with(
      "swiftc", "-O", VideoProbe.IOS_USB_RECORDER_SOURCE, "-o", binary
    )
    self.assertEqual(probe.ios_usb_recorder, binary)

  @unittest.skipIf(not _has_swift_toolchain(), "needs a macOS Swift toolchain")
  def test_ios_usb_recorder_source_typechecks(self):
    # Only runs on developer Macs; a full compile would take a few seconds,
    # type-checking catches the same mistakes without generating code.
    plt.PLATFORM.sh("swiftc", "-typecheck", VideoProbe.IOS_USB_RECORDER_SOURCE)


class VideoProbeContextIOSTestCase(unittest.TestCase):
  """The iOS device branches of the probe context, on a mocked context."""

  def setUp(self) -> None:
    self.tmp_dir = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp_dir.cleanup)
    self.result_path = pth.LocalPath(self.tmp_dir.name) / "video.mp4"
    self.context = mock.MagicMock(spec=VideoProbeContext)
    self.context.IOS_RECORDER_READY_WAIT = wait.WaitRange(
      min=dt.timedelta(milliseconds=10),
      max=dt.timedelta(milliseconds=10),
      timeout=dt.timedelta(milliseconds=300),
    )
    self.context.IOS_RECORDER_STOP_TIMEOUT = dt.timedelta(seconds=1)
    self.context.result_path = self.result_path
    self.context.local_result_path = self.result_path
    self.context._recorder_log_path = self.result_path.with_suffix(
      ".recorder.log"
    )
    self.context.host_platform = mock.MagicMock()
    self.context.probe = mock.MagicMock(
      FRAMERATE=60, ios_usb_recorder=pth.LocalPath("/out/recorder")
    )
    self.context._record_process = mock.MagicMock()
    self.context._record_process.poll.return_value = None
    self.context._recorder_log_file = None
    self.context._ios_recorder_is_ready = lambda: (
      VideoProbeContext._ios_recorder_is_ready(self.context)
    )
    self.context._stop_ios_recorder = lambda: (
      VideoProbeContext._stop_ios_recorder(self.context)
    )

  def _ios_platform(self, is_simulator: bool) -> mock.MagicMock:
    platform = mock.MagicMock(spec=IOSPlatform)
    platform.is_ios = True
    platform.is_linux = platform.is_macos = platform.is_android = False
    platform.is_simulator = is_simulator
    platform.model = "iPhone 18 - 3"
    return platform

  def test_default_result_path_is_local_on_ios(self):
    self.context.browser_platform = self._ios_platform(is_simulator=False)
    self.context.run.get_local_probe_result_path.return_value = self.result_path
    path = VideoProbeContext.get_default_result_path(self.context)
    self.assertEqual(path, self.result_path)
    self.context.run.get_local_probe_result_path.assert_called_once_with(
      self.context.probe
    )

  def test_recorder_platform(self):
    self.assertIsNotNone(VideoProbeContext._recorder_platform.fget)
    self.context.browser_platform = self._ios_platform(is_simulator=False)
    self.assertIs(
      VideoProbeContext._recorder_platform.fget(self.context),
      self.context.host_platform,
    )
    self.context.browser_platform = mock.MagicMock(is_ios=False)
    self.assertIs(
      VideoProbeContext._recorder_platform.fget(self.context),
      self.context.browser_platform,
    )

  def test_start_waits_for_ready_on_ios(self):
    self.context.browser_platform = self._ios_platform(is_simulator=False)
    self.context._recorder_platform = mock.MagicMock(is_remote=False)
    self.context._recorder_platform.popen.return_value.poll.return_value = None
    VideoProbeContext.start(self.context)
    self.context._recorder_platform.popen.assert_called_once()
    self.context._wait_for_ios_recorder_ready.assert_called_once_with()
    self.context.host_platform.sleep.assert_not_called()

  def test_teardown_does_not_copy_from_browser_on_ios(self):
    self.context.browser_platform = self._ios_platform(is_simulator=False)
    self.context._recorder_platform = mock.MagicMock()
    self.context._recorder_platform.is_file.return_value = True
    self.context.probe.generate_timestrip = False
    self.result_path.touch()
    result = VideoProbeContext.teardown(self.context)
    self.context.stop_process.assert_called_once_with()
    self.context.browser_result.assert_not_called()
    self.assertEqual(result.file, self.result_path)

  def test_record_cmd_device(self):
    self.context.browser_platform = self._ios_platform(is_simulator=False)
    cmd = VideoProbeContext._record_cmd(self.context, mock.MagicMock())
    self.assertEqual(
      cmd, ("/out/recorder", "iPhone 18 - 3", str(self.result_path), "60")
    )

  def test_wait_for_ios_recorder_ready(self):
    self.context._recorder_log_path.write_text(
      "starting\nREADY\n", encoding="utf-8"
    )
    VideoProbeContext._wait_for_ios_recorder_ready(self.context)
    self.context.host_platform.terminate_gracefully.assert_not_called()

  def test_wait_for_ios_recorder_ready_needs_whole_line(self):
    self.context._recorder_log_path.write_text(
      "NOT READY YET\n", encoding="utf-8"
    )
    with self.assertRaisesRegex(RuntimeError, "not ready after"):
      VideoProbeContext._wait_for_ios_recorder_ready(self.context)

  def test_wait_for_ios_recorder_ready_timeout_stops_recorder(self):
    with self.assertRaisesRegex(RuntimeError, "not ready after"):
      VideoProbeContext._wait_for_ios_recorder_ready(self.context)
    self.context.stop_process.assert_called_once_with()

  def test_wait_for_ios_recorder_ready_exited(self):
    self.context._record_process.poll.return_value = 1
    with self.assertRaisesRegex(RuntimeError, "exited before"):
      VideoProbeContext._wait_for_ios_recorder_ready(self.context)
    self.context.stop_process.assert_called_once_with()

  def test_stop_and_teardown_after_failed_start(self):
    self.context.browser_platform = self._ios_platform(is_simulator=False)
    self.context._record_process = None
    VideoProbeContext.stop(self.context)
    self.assertTrue(VideoProbeContext.teardown(self.context).is_empty)
    self.context.stop_process.assert_not_called()

  def test_stop_device_closes_stdin(self):
    self.context.browser_platform = self._ios_platform(is_simulator=False)
    # Running when stop() checks, exited cleanly once stdin was closed.
    self.context._record_process.poll.side_effect = [None, 0]
    VideoProbeContext.stop(self.context)
    self.context._record_process.communicate.assert_called_once_with(
      timeout=1.0
    )
    self.context.host_platform.terminate_gracefully.assert_not_called()
    self.context.stop_process.assert_not_called()

  def test_stop_device_reports_failed_recorder(self):
    self.context.browser_platform = self._ios_platform(is_simulator=False)
    self.context._record_process.poll.side_effect = [None, 1]
    with self.assertRaisesRegex(RuntimeError, "exit code 1"):
      VideoProbeContext.stop(self.context)
    # The unfinished file must not reach teardown().
    self.context.stop_process.assert_called_once_with()

  def test_stop_device_terminates_when_stuck(self):
    self.context.browser_platform = self._ios_platform(is_simulator=False)
    self.context._record_process.communicate.side_effect = (
      subprocess.TimeoutExpired("recorder", 1)
    )
    self.context._record_process.poll.side_effect = [None, -9]
    with self.assertRaisesRegex(RuntimeError, "exit code -9"):
      VideoProbeContext.stop(self.context)
    self.context.host_platform.terminate_gracefully.assert_called_once_with(
      self.context._record_process
    )
    self.context.stop_process.assert_called_once_with()

  def test_stop_device_keeps_file_finished_during_grace_period(self):
    self.context.browser_platform = self._ios_platform(is_simulator=False)
    self.context._record_process.communicate.side_effect = (
      subprocess.TimeoutExpired("recorder", 1)
    )
    # SIGTERM let it finish after all.
    self.context._record_process.poll.side_effect = [None, 0]
    VideoProbeContext.stop(self.context)
    self.context.stop_process.assert_not_called()


class VideoProbeContextAndroidTestCase(unittest.TestCase):
  def setUp(self) -> None:
    self.context = mock.MagicMock(spec=VideoProbeContext)
    self.context.ANDROID_RECORDER_STOP_TIMEOUT = dt.timedelta(seconds=2)
    self.context.result_path = pth.AnyPosixPath("/data/local/tmp/video.mp4")
    self.context.browser_platform = mock.MagicMock(
      is_android=True, is_linux=False, is_macos=False, is_ios=False
    )
    self.context.browser_platform.display_resolution.return_value = (
      DisplayResolution(2560, 1600)
    )
    self.context._scaled_android_size = lambda h: (
      VideoProbeContext._scaled_android_size(self.context, h)
    )
    self.context._android_record_cmd = lambda: (
      VideoProbeContext._android_record_cmd(self.context)
    )
    self.context._stop_android_recorder = lambda: (
      VideoProbeContext._stop_android_recorder(self.context)
    )

  def test_android_record_cmd_scales_and_sets_bitrate_and_unlimited(self):
    self.context.probe = VideoProbe.parse_dict(
      {
        "generate_timestrip": False,
        "merge_runs": False,
        "max_height": 480,
        "bit_rate": 1_000_000,
        "time_limit": 0,
        "codec_name": "c2.android.avc.encoder",
      }
    )
    cmd = VideoProbeContext._record_cmd(self.context, mock.MagicMock())
    self.assertEqual(
      cmd,
      (
        "screenrecord",
        "--codec-name",
        "c2.android.avc.encoder",
        "--size",
        "768x480",
        "--bit-rate",
        "1000000",
        "--time-limit",
        "0",
        pth.AnyPosixPath("/data/local/tmp/video.mp4"),
      ),
    )
    self.assertEqual(self.context._scaled_android_size(2000), (2560, 1600))

  def test_android_record_cmd_defaults(self):
    self.context.probe = VideoProbe.parse_dict(
      {
        "generate_timestrip": False,
        "merge_runs": False,
      }
    )
    cmd = VideoProbeContext._record_cmd(self.context, mock.MagicMock())
    self.assertEqual(
      cmd, ("screenrecord", pth.AnyPosixPath("/data/local/tmp/video.mp4"))
    )

  def test_stop_android_sends_sigint_and_waits(self):
    proc = mock.MagicMock()
    proc.poll.return_value = None
    self.context._record_process = proc
    VideoProbeContext.stop(self.context)
    self.context.browser_platform.send_signal.assert_called_once_with(
      proc, signal=self.context.browser_platform.signals.SIGINT
    )
    proc.wait.assert_called_once_with(timeout=2.0)

  def test_linux_record_cmd_uses_browser_platform_environ(self):
    context = mock.MagicMock(spec=VideoProbeContext)
    context.result_path = pth.AnyPosixPath("/tmp/video.mp4")
    context.browser_platform = mock.MagicMock(
      is_linux=True,
      is_posix=True,
      is_macos=False,
      is_android=False,
      is_ios=False,
      is_chromeos=False,
      is_win=False,
    )
    context.browser_platform.lookup_binary_override.return_value = None
    context.browser_platform.search_binary.return_value = pth.AnyPosixPath(
      "/usr/bin/ffmpeg"
    )
    context.browser_platform.environ = {"DISPLAY": ":99"}
    context.probe = VideoProbe.parse_dict(
      {"generate_timestrip": False, "merge_runs": False, "max_height": 480}
    )
    context._linux_record_cmd = lambda v: VideoProbeContext._linux_record_cmd(
      context, v
    )
    viewport = mock.MagicMock(has_size=True, x=10, y=20, width=800, height=600)
    with mock.patch.dict("os.environ", {"DISPLAY": ":20"}):
      cmd = VideoProbeContext._record_cmd(context, viewport)
    self.assertEqual(cmd[0], pth.AnyPosixPath("/usr/bin/ffmpeg"))
    self.assertEqual(cmd[-1], pth.AnyPosixPath("/tmp/video.mp4"))
    self.assertIn(":99+10,20", cmd)
    self.assertNotIn(":20+10,20", cmd)


class VideoProbePostProcessingTestCase(unittest.TestCase):
  """Post-processing of a recording, where timestrips are optional."""

  def setUp(self) -> None:
    self.tmp_dir = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp_dir.cleanup)
    self.tmp_path = pth.LocalPath(self.tmp_dir.name)
    self.result_path = self.tmp_path / "video.mp4"
    self.result_path.write_bytes(b"recording")
    self.strip_path = self.result_path.with_suffix(
      VideoProbe.TIMESTRIP_FILE_SUFFIX
    )
    self.merged_video = self.tmp_path / "merged.mp4"
    self.merged_strip = self.merged_video.with_suffix(
      VideoProbe.TIMESTRIP_FILE_SUFFIX
    )
    self.probe = VideoProbe.parse_dict({})
    self.context = self._create_mock_context()

  def _create_mock_context(self) -> mock.MagicMock:
    context = mock.MagicMock(spec=VideoProbeContext)
    context.result_path = self.result_path
    context.local_result_path = self.result_path
    context.probe = self.probe
    assert VideoProbeContext._timestrip_path.fget is not None
    context._timestrip_path = VideoProbeContext._timestrip_path.fget(context)
    context.FFMPEG_TIMELINE_TEXT = VideoProbeContext.FFMPEG_TIMELINE_TEXT
    context.IMAGE_FORMAT = VideoProbeContext.IMAGE_FORMAT
    context.TIMESTRIP_SCALE = VideoProbeContext.TIMESTRIP_SCALE
    context.host_platform = mock.MagicMock()
    context.host_platform.local_path = pth.LocalPath
    context.browser_platform = mock.MagicMock(is_ios=False)
    context._recorder_platform = mock.MagicMock()
    context._recorder_log_file = None
    context._record_process = mock.MagicMock()
    context.runner = mock.MagicMock()
    context.runner.platform.is_macos = False
    return context

  def _subprocess_error(self, *cmd: str) -> plt.SubprocessError:
    return plt.SubprocessError(
      plt.PLATFORM,
      subprocess.CompletedProcess(cmd, 1, b"", b"unable to read font"),
    )

  def _run_with_files(
    self, probe: VideoProbe, *files: pth.LocalPath
  ) -> mock.MagicMock:
    run = mock.MagicMock()
    run.results = {probe: mock.MagicMock(file_list=list(files))}
    return run

  def _mock_probe_host_platform(self) -> mock.MagicMock:
    patcher = mock.patch.object(
      VideoProbe, "host_platform", new_callable=mock.PropertyMock
    )
    mock_property = patcher.start()
    self.addCleanup(patcher.stop)
    host_platform = mock_property.return_value
    host_platform.is_macos = False
    return host_platform

  def _assert_create_time_strip_warns(self, error: Exception) -> None:
    self.strip_path.touch()
    self.context._create_time_strip.side_effect = error
    with self.assertLogs(level="WARNING") as logs:
      self.assertIsNone(VideoProbeContext._try_create_time_strip(self.context))
    self.assertFalse(self.strip_path.exists())
    self.assertEqual(len(logs.output), 1)
    self.assertIn("Could not create timestrip", logs.output[0])
    self.assertIn("generate_timestrip:false", logs.output[0])

  def _assert_merge_timestrips_warns(self, error: Exception) -> None:
    host_platform = self._mock_probe_host_platform()
    host_platform.sh.side_effect = error
    run = self._run_with_files(self.probe, self.result_path, self.strip_path)
    self.merged_strip.touch()
    with self.assertLogs(level="WARNING") as logs:
      self.assertIsNone(
        self.probe._try_merge_timestrips((run, run), self.merged_video)
      )
    self.assertFalse(self.merged_strip.exists())
    self.assertIn("Could not merge timestrips", logs.output[0])

  def test_timestrip_path(self):
    self.assertEqual(self.context._timestrip_path, self.strip_path)

  def test_try_create_time_strip(self):
    self.context._create_time_strip.return_value = self.strip_path
    self.assertEqual(
      VideoProbeContext._try_create_time_strip(self.context), self.strip_path
    )

  def test_try_create_time_strip_subprocess_error_warns(self):
    self._assert_create_time_strip_warns(self._subprocess_error("montage"))

  def test_try_create_time_strip_missing_binary_warns(self):
    self._assert_create_time_strip_warns(FileNotFoundError("montage"))

  def test_teardown_keeps_recording_without_timestrip(self):
    self.context._try_create_time_strip.return_value = None
    result = VideoProbeContext.teardown(self.context)
    self.assertEqual(result.file_list, [self.result_path])

  def test_teardown_with_timestrip(self):
    self.strip_path.touch()
    self.context._try_create_time_strip.return_value = self.strip_path
    result = VideoProbeContext.teardown(self.context)
    # The recording is not re-encoded or moved for the timestrip.
    self.context.host_platform.sh.assert_not_called()
    self.assertEqual(self.result_path.read_bytes(), b"recording")
    self.assertEqual(result.file_list, [self.result_path, self.strip_path])

  def test_create_time_strip(self):
    strip = VideoProbeContext._create_time_strip(self.context, self.tmp_path)
    self.assertEqual(strip, self.strip_path)
    self.context.host_platform.sh.assert_called_once()
    ffmpeg_args = self.context.host_platform.sh.call_args.args
    fflags_index = ffmpeg_args.index("-fflags")
    i_index = ffmpeg_args.index("-i")
    self.assertLess(fflags_index, i_index)
    self.assertEqual(ffmpeg_args[fflags_index + 1], "+igndts")
    filter_graph = ffmpeg_args[ffmpeg_args.index("-filter_complex") + 1]
    self.assertEqual(
      filter_graph,
      f"trim=duration=2,fps=20,{VideoProbeContext.FFMPEG_TIMELINE_TEXT},"
      f"{VideoProbeContext.TIMESTRIP_SCALE}",
    )

  def test_try_merge_timestrips_none_available(self):
    host_platform = self._mock_probe_host_platform()
    run = self._run_with_files(self.probe, self.result_path)
    self.assertIsNone(
      self.probe._try_merge_timestrips((run, run), self.merged_video)
    )
    host_platform.sh.assert_not_called()

  def test_try_merge_timestrips_skips_runs_without_strip(self):
    host_platform = self._mock_probe_host_platform()
    run_without_strip = self._run_with_files(self.probe, self.result_path)
    run_with_strip = self._run_with_files(
      self.probe, self.result_path, self.strip_path
    )
    result = self.probe._try_merge_timestrips(
      (run_without_strip, run_with_strip), self.merged_video
    )
    self.assertEqual(result, self.merged_strip)
    host_platform.sh.assert_called_once()
    args = host_platform.sh.call_args.args
    self.assertEqual(args[:2], ("montage", self.strip_path))
    self.assertEqual(args[-1], self.merged_strip)

  def test_try_merge_timestrips_subprocess_error_warns(self):
    self._assert_merge_timestrips_warns(self._subprocess_error("montage"))

  def test_try_merge_timestrips_missing_binary_warns(self):
    self._assert_merge_timestrips_warns(FileNotFoundError("montage"))

  def test_merge_repetitions_without_timestrips(self):
    self._mock_probe_host_platform()
    self.merged_video.touch()
    run = self._run_with_files(self.probe, self.result_path)
    group = mock.MagicMock(runs=(run, run))
    group.get_local_probe_result_path.return_value = self.merged_video
    result = self.probe.merge_repetitions(group)
    self.assertEqual(result.file_list, [self.merged_video])

  def test_merge_repetitions_with_timestrip(self):
    self._mock_probe_host_platform()
    self.merged_video.touch()
    self.merged_strip.touch()
    run = self._run_with_files(self.probe, self.result_path, self.strip_path)
    group = mock.MagicMock(runs=(run, run))
    group.get_local_probe_result_path.return_value = self.merged_video
    result = self.probe.merge_repetitions(group)
    self.assertEqual(result.file_list, [self.merged_video, self.merged_strip])

  def test_montage_cmd(self):
    font = VideoProbe.MACOS_MONTAGE_FONT
    platform = mock.MagicMock(is_macos=True)
    platform.is_file.return_value = True
    self.assertEqual(
      self.probe.montage_cmd(platform), ("montage", "-font", font)
    )
    platform.is_file.assert_called_once_with(font)
    platform.is_file.return_value = False
    self.assertEqual(self.probe.montage_cmd(platform), ("montage",))
    platform = mock.MagicMock(is_macos=False)
    self.assertEqual(self.probe.montage_cmd(platform), ("montage",))
    platform.is_file.assert_not_called()

  def test_merge_timestrips_passes_macos_font(self):
    font = VideoProbe.MACOS_MONTAGE_FONT
    host_platform = self._mock_probe_host_platform()
    host_platform.is_macos = True
    host_platform.is_file.return_value = True
    run = self._run_with_files(self.probe, self.result_path, self.strip_path)
    self.probe._try_merge_timestrips((run, run), self.merged_video)
    self.assertEqual(
      host_platform.sh.call_args.args[:4],
      ("montage", "-font", font, self.strip_path),
    )

  def test_create_time_strip_passes_macos_font(self):
    font = VideoProbe.MACOS_MONTAGE_FONT
    self.context.runner.platform.is_macos = True
    self.context.runner.platform.is_file.return_value = True
    VideoProbeContext._create_time_strip(self.context, self.tmp_path)
    self.assertEqual(
      self.context.runner.platform.sh.call_args.args[:4],
      ("montage", "-font", font, f"{self.tmp_path}/timeline/*.png"),
    )

  def test_merge_repetitions_does_not_upscale(self):
    host_platform = self._mock_probe_host_platform()
    probe = VideoProbe.parse_dict({"generate_timestrip": False})
    self.merged_video.touch()
    run = self._run_with_files(probe, self.result_path)
    group = mock.MagicMock(runs=(run, run))
    group.get_local_probe_result_path.return_value = self.merged_video
    result = probe.merge_repetitions(group)
    self.assertEqual(result.file_list, [self.merged_video])
    ffmpeg_args = host_platform.sh.call_args.args
    filter_graph = ffmpeg_args[ffmpeg_args.index("-filter_complex") + 1]
    self.assertTrue(filter_graph.startswith("hstack=inputs=2,fps=60,drawtext="))
    self.assertTrue(filter_graph.endswith(",scale='min(3000,iw)':-2"))

  def _story_group(self, story_name: str) -> mock.MagicMock:
    story = mock.MagicMock()
    story.name = story_name
    rep_group = self._run_with_files(self.probe, self.result_path)
    rep_group.story = story
    return rep_group

  def test_merge_stories_for_browser_limits_framerate(self):
    host_platform = self._mock_probe_host_platform()
    rep_group = self._story_group("story")
    result = self.probe._merge_stories_for_browser(
      self.tmp_path, rep_group.story, [rep_group, rep_group]
    )
    self.assertEqual(result, self.tmp_path / "story_combined.mp4")
    ffmpeg_args = host_platform.sh.call_args.args
    filter_graph = ffmpeg_args[ffmpeg_args.index("-filter_complex") + 1]
    self.assertEqual(filter_graph, "vstack=inputs=2,fps=60")

  def _scaled_frame_size(
    self, scale_filter: str, width: int, height: int
  ) -> tuple[int, int]:
    frame = self.tmp_path / f"{width}x{height}.png"
    plt.PLATFORM.sh(
      "ffmpeg",
      "-hide_banner",
      "-f",
      "lavfi",
      "-i",
      f"color=size={width}x{height}",
      "-filter_complex",
      scale_filter,
      "-frames:v",
      "1",
      frame,
      quiet=True,
    )
    # The PNG IHDR chunk starts with the big-endian width and height.
    header = frame.read_bytes()[16:24]
    scaled_width, scaled_height = struct.unpack(">II", header)
    return scaled_width, scaled_height

  @unittest.skipIf(
    not Binaries.FFMPEG.search(plt.PLATFORM), "needs a local ffmpeg"
  )
  def test_merged_video_scale_with_ffmpeg(self):
    scale = VideoProbe.MERGED_VIDEO_SCALE
    # Two portrait phone recordings side by side: used to be scaled up.
    self.assertEqual(self._scaled_frame_size(scale, 2160, 2404), (2160, 2404))
    # Wider videos are scaled down to an even height, keeping aspect ratio.
    self.assertEqual(self._scaled_frame_size(scale, 4000, 2404), (3000, 1804))

  @unittest.skipIf(
    not Binaries.FFMPEG.search(plt.PLATFORM), "needs a local ffmpeg"
  )
  def test_timestrip_scale_with_ffmpeg(self):
    scale = VideoProbeContext.TIMESTRIP_SCALE
    # Shorter frames are left at their original resolution.
    self.assertEqual(self._scaled_frame_size(scale, 120, 80), (120, 80))
    # Taller frames are scaled down to 100 px high, keeping aspect ratio.
    self.assertEqual(self._scaled_frame_size(scale, 1080, 2404), (45, 100))

  def _touch_last_arg(self, *args: object) -> None:
    output = args[-1]
    assert isinstance(output, pth.LocalPath)
    output.write_bytes(b"merged")

  def test_merge_repetitions_disabled(self):
    host_platform = self._mock_probe_host_platform()
    probe = VideoProbe.parse_dict({"merge_runs": False})
    self.assertTrue(probe.merge_repetitions(mock.MagicMock()).is_empty)
    host_platform.sh.assert_not_called()

  def test_merge_repetitions_single_run_copies_files(self):
    host_platform = self._mock_probe_host_platform()
    host_platform.copy.side_effect = shutil.copyfile
    self.strip_path.write_bytes(b"strip")
    out_dir = self.tmp_path / "group"
    out_dir.mkdir()
    run = self._run_with_files(self.probe, self.result_path, self.strip_path)
    group = mock.MagicMock(path=out_dir, runs=(run,))
    result = self.probe.merge_repetitions(group)
    self.assertEqual(
      result.file_list,
      [out_dir / self.result_path.name, out_dir / self.strip_path.name],
    )
    host_platform.sh.assert_not_called()

  def test_merge_browsers_single_group_delegates(self):
    host_platform = self._mock_probe_host_platform()
    group = mock.MagicMock(runs=(), repetitions_groups=[mock.MagicMock()])
    self.assertTrue(self.probe.merge_browsers(group).is_empty)
    host_platform.sh.assert_not_called()

  def test_merge_browsers_groups_by_story(self):
    host_platform = self._mock_probe_host_platform()
    host_platform.sh.side_effect = self._touch_last_arg
    host_platform.copy.side_effect = shutil.copyfile
    rep_a1 = self._story_group("story_a")
    rep_a2 = self._story_group("story_a")
    rep_a2.story = rep_a1.story
    rep_b = self._story_group("story_b")
    browsers_path = self.tmp_path / "browsers" / "video.mp4"
    group = mock.MagicMock(repetitions_groups=[rep_a1, rep_a2, rep_b])
    group.get_local_probe_result_path.return_value = browsers_path

    result = self.probe.merge_browsers(group)
    combined_dir = browsers_path / "video"
    self.assertCountEqual(
      result.file_list,
      [
        combined_dir / "story_a_combined.mp4",
        combined_dir / "story_b_combined.mp4",
      ],
    )
    host_platform.sh.assert_called_once()
    host_platform.copy.assert_called_once_with(
      self.result_path, combined_dir / "story_b_combined.mp4"
    )

  def test_merge_stories_for_browser_error_reraises(self):
    host_platform = self._mock_probe_host_platform()
    host_platform.sh.side_effect = self._subprocess_error("ffmpeg")
    rep_group = self._story_group("story")
    with self.assertLogs(level="ERROR") as logs:
      self.assertRaises(
        plt.SubprocessError,
        self.probe._merge_stories_for_browser,
        self.tmp_path,
        rep_group.story,
        [rep_group, rep_group],
      )
    self.assertIn("Merging multiple browser video failed", logs.output[0])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
