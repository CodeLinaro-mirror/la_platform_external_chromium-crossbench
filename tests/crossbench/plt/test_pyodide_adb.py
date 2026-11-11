# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import io
import json
import pathlib
import shlex
import subprocess
from typing import TYPE_CHECKING, override
from unittest import mock

from crossbench.action_runner.input_events import TouchEvent
from crossbench.action_runner.virtual_device.touchscreen import \
    TouchscreenVirtualDeviceConfig
from crossbench.benchmarks.loading.point import Point
from crossbench.cli.config.driver import BrowserDriverType, DriverConfig
from crossbench.plt.android_adb import AndroidAdbPlatform, AndroidDeviceInfo
from crossbench.plt.arch import MachineArch
from crossbench.plt.base import Platform
from crossbench.plt.pyodide_adb import PyodideAdb, PyodideAndroidAdbPlatform, \
    PyodideGcsBlob, PyodidePlatform, PyodideStreamingPopen, is_pyodide_env
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.mock_helper import LinuxMockPlatform, \
    PyodideMockPlatform, ShResult, ShResultType
from tests.crossbench.plt.test_android_adb import AndroidAdbMockPlatformTest
from tests.crossbench.plt.test_linux import LocalLinuxMockPlatformTestCase

if TYPE_CHECKING:
  from crossbench import path as pth
  from crossbench.plt.types import CmdArg

MOCK_GCS_FILE_SIZE: int = 45678


class MockJsBuffer:

  def __init__(self, data: bytes) -> None:
    self._data: bytes = data

  def to_bytes(self) -> bytes:
    return self._data


class MockWebAdb:

  def __init__(self, serial: str = "mock-serial-123") -> None:
    self.serial = serial
    self.shell_calls: list[str] = []
    self.shell_inputs: list[str | None] = []
    self._expected_sh_cmds: list[str] | None = None
    self._sh_results: list[ShResult] = []
    self.push_calls: list[tuple[str, str]] = []
    self.pull_calls: list[tuple[str, str]] = []
    self.forward_calls: list[tuple[str, str]] = []
    self.reverse_calls: list[tuple[str, str]] = []
    self.gcs_downloads: list[tuple[str, str]] = []
    self.is_interrupted: bool = False
    self.spawned_processes: list[str] = []
    self.killed_processes: list[int] = []
    self.process_logs: dict[int, list[str]] = {}
    self.process_stdin: dict[int, list[str]] = {}
    self.closed_stdin_processes: list[int] = []
    self._next_proc_id: int = 100

  @property
  def expected_sh_cmds(self) -> list[str] | None:
    if self._expected_sh_cmds is None:
      return None
    return list(self._expected_sh_cmds)

  def expect_sh(
      self,
      *args: CmdArg | int,
      result: ShResultType = "",
      returncode: int = 0,
  ) -> None:
    if args:
      if self._expected_sh_cmds is None:
        self._expected_sh_cmds = []
      cmd_str = (str(args[0]) if len(args) == 1 else shlex.join(map(str, args)))
      self._expected_sh_cmds.append(cmd_str)
    if isinstance(result, (str, bytes)):
      result = ShResult(result, returncode)
    else:
      assert returncode == 0, "Cannot have ShResult and custom returncode"
    assert isinstance(result, ShResult)
    self._sh_results.append(result)

  def spawnProcess(self, cmd: str) -> int:  # noqa: N802
    self.spawned_processes.append(cmd)
    self._next_proc_id += 1
    return self._next_proc_id

  def writeProcessStdin(  # noqa: N802
      self,
      proc_id: int,
      data: str,
  ) -> None:
    self.process_stdin.setdefault(proc_id, []).append(data)

  def closeProcessStdin(self, proc_id: int) -> None:  # noqa: N802
    self.closed_stdin_processes.append(proc_id)
    self.process_logs.setdefault(proc_id, []).append(
        json.dumps({
            "text": "",
            "nextOffset": 1,
            "isExited": True,
            "exitCode": 0,
        }))

  def killProcess(self, proc_id: int) -> None:  # noqa: N802
    self.killed_processes.append(proc_id)

  def readProcessLog(self, proc_id: int, offset: int) -> str:  # noqa: N802
    logs = self.process_logs.get(proc_id, [])
    if offset < len(logs):
      return logs[offset]
    return ""

  def shell(
      self,
      cmd: str,
      input: str | None = None,  # pylint: disable=redefined-builtin
  ) -> str | bytes:
    if self._expected_sh_cmds is not None:
      assert self._expected_sh_cmds, (
          f"Missing expected sh_cmds, but got: {cmd}")
      expected = self._expected_sh_cmds.pop(0)
      assert expected == cmd, (f"After {len(self.shell_calls)} cmds:\n"
                               f"  expected: {expected!r}\n"
                               f"  got:      {cmd!r}")
    self.shell_calls.append(cmd)
    self.shell_inputs.append(input)
    if self._sh_results:
      return self._sh_results.pop(0).result
    if self._expected_sh_cmds is not None:
      raise ValueError(f"After {len(self.shell_calls)} cmds: "
                       f"MockWebAdb has no more sh outputs for cmd: {cmd}")
    return f"mock_out: {cmd}"

  def push(self, src: str, dest: str) -> None:
    self.push_calls.append((src, dest))

  def pull(self, src: str, dest: str) -> None:
    self.pull_calls.append((src, dest))

  def forward(self, local: str, remote: str) -> None:
    self.forward_calls.append((local, remote))

  def forwardRemove(self, local: str) -> None:  # noqa: N802
    self.forward_calls.append(("--remove", local))

  def reverse(self, remote: str, local: str) -> None:
    self.reverse_calls.append((remote, local))

  def reverseRemove(self, remote: str) -> None:  # noqa: N802
    self.reverse_calls.append(("--remove", remote))

  def root(self) -> None:
    pass

  def unroot(self) -> None:
    pass

  def sendCdpCommand(self, method: str, params: str) -> str:  # noqa: N802
    return "{}"

  def startDevTools(self) -> str:  # noqa: N802
    return "OK"

  def stopDevTools(self) -> str:  # noqa: N802
    return "OK"

  def switchTab(self, url: str = "about:blank") -> str:  # noqa: N802
    del url
    return "mock_session_1"

  def gcsGetMetadata(self, url: str) -> str:  # noqa: N802
    del url
    return json.dumps({
        "md5Hash": "mock_hash_123",
        "size": MOCK_GCS_FILE_SIZE,
    })

  def gcsDownloadFile(self, url: str, dest: str) -> None:  # noqa: N802
    self.gcs_downloads.append((url, dest))
    dest_path = pathlib.Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(b"\0" * MOCK_GCS_FILE_SIZE)

  def isInterrupted(self) -> bool:  # noqa: N802
    return self.is_interrupted

  def acknowledgeInterrupt(self) -> None:  # noqa: N802
    self.is_interrupted = False


class PyodideMockPlatformTestCase(LocalLinuxMockPlatformTestCase):
  __test__ = True
  platform: PyodideMockPlatform

  @override
  def setup_host_platform(self) -> PyodideMockPlatform:
    self.webadb = MockWebAdb()
    return PyodideMockPlatform(webadb=self.webadb)

  @override
  def test_is_pyodide(self) -> None:
    self.assertTrue(self.platform.is_pyodide)

  def test_is_pyodide_env(self) -> None:
    with mock.patch("sys.platform", "linux"):
      with mock.patch.dict("sys.modules", {}, clear=True):
        self.assertFalse(is_pyodide_env())
    with mock.patch("sys.platform", "emscripten"):
      self.assertTrue(is_pyodide_env())

  def test_driver_config_pyodide(self) -> None:
    mock_js = mock.MagicMock()
    mock_js.webadb = self.webadb
    with mock.patch("crossbench.plt.pyodide.js", mock_js), \
         mock.patch("crossbench.plt.pyodide_adb.js", mock_js), \
         mock.patch("crossbench.plt.PLATFORM", self.platform):
      driver_config = DriverConfig(driver_type=BrowserDriverType.ANDROID_CDP)
      plt = driver_config.get_platform()
      self.assertIsInstance(plt, PyodideAndroidAdbPlatform)

  def test_machine_wasm(self) -> None:
    with mock.patch("platform.machine", return_value="wasm32"):
      mock_plt = mock.MagicMock(spec=Platform)
      mock_plt._raw_machine_arch.side_effect = lambda: "wasm32"
      self.assertEqual(
          Platform.machine.func(mock_plt),  # type: ignore[attr-defined]
          MachineArch.WASM_32,
      )
    with mock.patch("platform.machine", return_value="wasm64"):
      mock_plt = mock.MagicMock(spec=Platform)
      mock_plt._raw_machine_arch.side_effect = lambda: "wasm64"
      self.assertEqual(
          Platform.machine.func(mock_plt),  # type: ignore[attr-defined]
          MachineArch.WASM_64,
      )

  def test_gcs_blob(self) -> None:
    blob = PyodideGcsBlob(
        "gs://chrome-partner-loadline/test.wprgo", webadb=self.webadb)
    blob.reload()
    self.assertEqual(blob.md5_hash, "mock_hash_123")
    self.assertEqual(blob.size, MOCK_GCS_FILE_SIZE)
    self.assertTrue(blob.exists())

    blob.download_to_filename("/cache/wpr/test.wprgo")
    self.assertEqual(
        self.webadb.gcs_downloads[-1],
        ("gs://chrome-partner-loadline/test.wprgo", "/cache/wpr/test.wprgo"),
    )

  def test_pyodide_platform_gcs(self) -> None:
    url = "gs://chrome-partner-loadline/archive_phone_20260331.wprgo"
    blob = self.platform.prepare_gcs_request(url)
    self.assertEqual(blob.md5_hash, "mock_hash_123")
    self.assertTrue(self.platform.check_gcs_file_exists(url))

    dest = self.platform.local_path("/cache/wpr/archive.wprgo")
    self.platform.download_gcs_file(url, dest)
    self.assertEqual(self.webadb.gcs_downloads[-1],
                     (url, "/cache/wpr/archive.wprgo"))
    self.assertEqual(dest.stat().st_size, MOCK_GCS_FILE_SIZE)


class PyodideAdbTest(CrossbenchFakeFsTestCase):
  __test__ = True

  def setUp(self) -> None:
    super().setUp()
    self.platform = LinuxMockPlatform()
    self.webadb = MockWebAdb()
    self.adb = PyodideAdb(
        host_platform=self.platform,
        device_identifier="mock-serial-123",
        webadb=self.webadb,
    )

  def test_basic_properties(self) -> None:
    self.assertEqual(self.adb.serial_id, "mock-serial-123")
    devices = self.adb.devices()
    self.assertIn("mock-serial-123", devices)

  def test_shell(self) -> None:
    res = self.adb.shell("echo", "hello world")
    self.assertEqual(res.returncode, 0)
    self.assertIn("echo 'hello world'", self.webadb.shell_calls[0])

  def test_shell_true_and_false(self) -> None:
    res = self.adb.shell(
        "echo 'hello world' > /data/local/tmp/test", shell=True)
    self.assertEqual(res.returncode, 0)
    self.assertEqual(
        self.webadb.shell_calls[-1],
        "echo 'hello world' > /data/local/tmp/test",
    )
    with self.assertRaises(ValueError):
      self.adb.shell("echo", "hello", "world", shell=True)

  def test_push_pull(self) -> None:
    src_p = str(self.platform.path("/src/file"))
    dest_p = str(self.platform.path("/dest/file"))
    self.adb.push(
        self.platform.local_path("/src/file"),
        self.platform.local_path("/dest/file"),
    )
    self.assertEqual(self.webadb.push_calls[0], (src_p, dest_p))
    self.adb.pull(
        self.platform.local_path("/dest/file"),
        self.platform.local_path("/src/file"),
    )
    self.assertEqual(self.webadb.pull_calls[0], (dest_p, src_p))

  def test_shell_stdout(self) -> None:
    out = self.adb.shell_stdout("echo", "hello")
    self.assertEqual(out, "mock_out: echo hello")

  def test_shell_js_buffer_and_bytes(self) -> None:
    js_buf = MockJsBuffer(b"package:com.android.chrome\n")
    with mock.patch.object(self.webadb, "shell", return_value=js_buf):
      self.assertEqual(
          self.adb.shell_stdout_bytes("pm", "list", "packages"),
          b"package:com.android.chrome\n",
      )
      self.assertEqual(
          self.adb.shell_stdout("pm", "list", "packages"),
          "package:com.android.chrome\n",
      )
    self.assertEqual(self.adb._to_bytes(b"abc"), b"abc")
    self.assertEqual(self.adb._to_bytes("xyz"), b"xyz")

  def test_shell_input(self) -> None:
    res = self.adb.shell(
        "tee", "/sys/kernel/tracing/trace_marker", input=b"I|0|mark\n")
    self.assertEqual(res.returncode, 0)
    self.assertEqual(
        self.webadb.shell_calls[-1],
        "tee /sys/kernel/tracing/trace_marker",
    )
    self.assertEqual(self.webadb.shell_inputs[-1], "I|0|mark\n")
    out = self.adb.shell_stdout_bytes("cat", input=b"hello\n")
    self.assertEqual(self.webadb.shell_calls[-1], "cat")
    self.assertEqual(self.webadb.shell_inputs[-1], "hello\n")
    self.assertEqual(out, b"mock_out: cat")

  def test_adb_shell(self) -> None:
    res = self.adb._adb("shell", "echo", "hello")
    self.assertEqual(res.returncode, 0)
    self.assertIn("echo hello", self.webadb.shell_calls[-1])
    with self.assertRaises(NotImplementedError):
      self.adb._adb("install", "foo.apk")
    with self.assertRaises(NotImplementedError):
      self.adb._adb("push", "/src", "/dest")

  def test_forward_reverse(self) -> None:
    with self.assertRaises(NotImplementedError):
      self.adb.forward(1234, 5678)
    with self.assertRaises(NotImplementedError):
      self.adb.forward_remove(1234)
    with self.assertRaises(NotImplementedError):
      self.adb.reverse(1234, 5678)
    with self.assertRaises(NotImplementedError):
      self.adb.reverse_remove(1234)


class PyodideAndroidAdbPlatformTest(AndroidAdbMockPlatformTest):
  __test__ = True
  DEVICE_ID = "mock-serial-123"
  platform: PyodideAndroidAdbPlatform
  adb: PyodideAdb
  host_platform: PyodideMockPlatform

  @override
  def setup_host_platform(self) -> PyodideMockPlatform:
    self.webadb = MockWebAdb(serial=self.DEVICE_ID)
    return PyodideMockPlatform(webadb=self.webadb)

  @override
  def setup_platform(self) -> PyodideAndroidAdbPlatform:
    self.adb = PyodideAdb(
        host_platform=self.host_platform,
        device_identifier=self.DEVICE_ID,
        webadb=self.webadb,
    )
    platform = PyodideAndroidAdbPlatform(
        host_platform=self.host_platform,
        device_identifier=self.DEVICE_ID,
        adb=self.adb,
        webadb=self.webadb,
    )
    self.mock_platform_str(platform, "adb.mock_platform.arm64")
    return platform

  @override
  def tearDown(self) -> None:
    expected_sh_cmds = self.webadb.expected_sh_cmds
    if expected_sh_cmds is not None:
      self.assertSequenceEqual(expected_sh_cmds, [],
                               "Got additional unused webadb shell cmds.")
    super().tearDown()

  @override
  def expect_sh(
      self,
      *args: CmdArg | int,
      result: ShResultType = "",
      returncode: int = 0,
  ) -> None:
    self.webadb.expect_sh(*args, result=result, returncode=returncode)

  @override
  def expect_path_check(
      self,
      flag: str,
      path: pth.AnyPathLike,
      exists: bool = True,
  ) -> None:
    quoted_path = shlex.quote(str(self.platform.path(path)))
    self.expect_sh(
        f"[ {flag} {quoted_path} ] && echo 1",
        result="1\n" if exists else "",
    )

  @override
  def test_is_pyodide(self) -> None:
    self.assertTrue(self.platform.is_pyodide)

  @override
  def test_adb_basic_properties(self) -> None:
    self.assertEqual(self.adb.serial_id, self.DEVICE_ID)
    self.assertEqual(
        self.adb.device_info,
        AndroidDeviceInfo(device_id=self.DEVICE_ID, name="device"),
    )
    self.assertIn(self.DEVICE_ID, str(self.adb))

  def test_platform_properties(self) -> None:
    self.assertTrue(self.platform.is_android)
    self.assertEqual(self.platform.os_name, "android")
    self.assertEqual(self.platform.serial_id, self.DEVICE_ID)
    self.assertEqual(self.platform.key, ("android", self.DEVICE_ID))

  def test_sh(self) -> None:
    res = self.platform.sh("echo", "test")
    self.assertEqual(res.returncode, 0)
    self.assertIsInstance(res.stdout, bytes)
    self.assertIsInstance(res.stderr, bytes)
    self.assertEqual(res.stdout, b"mock_out: echo test")
    self.assertEqual(self.webadb.shell_calls[0], "echo test")
    self.expect_sh("echo hello", result="hello\n")
    res_with_output = self.platform.sh("echo", "hello")
    self.assertEqual(res_with_output.stdout, b"hello\n")
    self.expect_sh("echo hello", result="hello\n")
    self.assertEqual(self.platform.sh_stdout("echo", "hello"), "hello\n")

  def test_push_pull(self) -> None:
    src_file = self.host_platform.local_path("/src/file.txt")
    dest_file = self.platform.path("/sdcard/file.txt")
    self.platform.push(src_file, dest_file)
    self.assertEqual(self.webadb.push_calls[-1],
                     (str(src_file), str(dest_file)))

    pull_dest = self.host_platform.local_path("/tmp/download.txt")
    self.expect_path_check("-e", dest_file)
    self.platform.pull(dest_file, pull_dest)
    self.assertEqual(self.webadb.pull_calls[-1],
                     (str(dest_file), str(pull_dest)))

    self.expect_path_check("-e", dest_file, exists=False)
    with self.assertRaises(ValueError):
      self.platform.pull(dest_file, pull_dest)

  def test_send_cdp_command(self) -> None:
    with mock.patch.object(
        self.webadb,
        "sendCdpCommand",
        return_value='{"frameId": "mock_frame_123"}',
    ) as mock_send:
      res = self.platform.send_cdp_command("Page.navigate",
                                           {"url": "https://example.com"})
      mock_send.assert_called_once_with("Page.navigate",
                                        '{"url": "https://example.com"}')
      self.assertEqual(res, {"id": 1, "result": {"frameId": "mock_frame_123"}})

  def test_switch_to_new_tab(self) -> None:
    with mock.patch.object(
        self.webadb, "switchTab", return_value="session_123") as mock_switch:
      self.platform.switch_to_new_tab("https://example.com")
      mock_switch.assert_called_once_with("https://example.com")

  def test_start_devtools(self) -> None:
    with mock.patch.object(
        self.webadb, "startDevTools", return_value="OK") as mock_start:
      self.platform.start_devtools()
      mock_start.assert_called_once()

  def test_start_devtools_failure(self) -> None:
    with mock.patch.object(self.webadb, "startDevTools", return_value=""):
      with self.assertRaises(RuntimeError):
        self.platform.start_devtools()

  def test_stop_devtools(self) -> None:
    with mock.patch.object(
        self.webadb, "stopDevTools", return_value="OK") as mock_stop:
      self.platform.stop_devtools()
      mock_stop.assert_called_once()

  def test_pyodide_android_adb_platform_gcs(self) -> None:
    url = "gs://chrome-partner-loadline/archive_phone_20260331.wprgo"
    blob = self.platform.prepare_gcs_request(url)
    self.assertEqual(blob.md5_hash, "mock_hash_123")
    self.assertTrue(self.platform.check_gcs_file_exists(url))

    dest = self.host_platform.local_path("/cache/wpr/archive.wprgo")
    self.platform.download_gcs_file(url, dest)
    self.assertEqual(self.webadb.gcs_downloads[-1],
                     (url, "/cache/wpr/archive.wprgo"))
    self.assertEqual(dest.stat().st_size, MOCK_GCS_FILE_SIZE)

  def test_interrupted(self) -> None:
    self.webadb.is_interrupted = True
    with self.assertRaises(KeyboardInterrupt):
      self.platform.sleep(1)
    self.assertFalse(self.webadb.is_interrupted)

  @override
  def test_port_forward_default(self) -> None:
    with self.assertRaises(NotImplementedError):
      self.platform.ports.forward(0, 33221)

  @override
  def test_port_forward(self) -> None:
    with self.platform.ports.nested() as ports:
      with self.assertRaises(NotImplementedError):
        ports.forward(0, 33221)

  @override
  def test_port_forward_auto_close(self) -> None:
    pass

  @override
  def test_reverse_port_forward_default(self) -> None:
    with self.assertRaises(NotImplementedError):
      self.platform.ports.reverse_forward(0, 33221)

  @override
  def test_reverse_port_forward(self) -> None:
    with self.platform.ports.nested() as ports:
      with self.assertRaises(NotImplementedError):
        ports.reverse_forward(0, 33221)

  @override
  def test_reverse_port_forward_nested_auto_close(self) -> None:
    pass

  @override
  def test_reverse_port_forward_auto_close(self) -> None:
    pass

  @override
  def test_popen_kill_all_sends_remote_adb_kill(self) -> None:
    self.expect_sh("kill -9 101")
    proc = self.platform.popen("sleep", "5")
    self.assertIsInstance(proc, PyodideStreamingPopen)
    self.assertEqual(self.platform.active_popens, (proc,))
    self.assertEqual(self.host_platform.active_popens, ())

    self.platform.kill_all_popens()
    self.assertEqual(self.webadb.shell_calls[-1], "kill -9 101")

  @override
  def test_trace_mark(self) -> None:
    super().test_trace_mark()
    self.assertEqual(self.webadb.shell_inputs[-1],
                     "I|0|crossbench-android-mark\n")

  @override
  def test_sh_input(self) -> None:
    self.expect_sh("cat", result="hello world")
    hello_world = self.platform.sh_stdout("cat", input=b"hello world")
    self.assertEqual(hello_world, "hello world")
    self.assertEqual(self.webadb.shell_inputs[-1], "hello world")

    self.expect_sh("cat", result=b"hello world bytes")
    hello_world_bytes = self.platform.sh_stdout_bytes(
        "cat", input=b"hello world bytes")
    self.assertEqual(hello_world_bytes, b"hello world bytes")
    self.assertEqual(self.webadb.shell_inputs[-1], "hello world bytes")

  def test_uinput_end_to_end_via_webadb(self) -> None:
    with (
        self.patch_getprop(AndroidAdbPlatform.MIN_UINPUT_SDK_VERSION),
        mock.patch.object(self.platform, "sleep"),
    ):
      self.platform.setup_virtual_devices((TouchscreenVirtualDeviceConfig(
          name="touch1", width=1080, height=2400),))
      self.assertEqual(self.webadb.spawned_processes, ["uinput -"])
      self.assertIn("touch1", self.platform._virtual_devices)
      proc_id = self.platform._virtual_devices["touch1"].proc.pid
      self.assertEqual(len(self.webadb.process_stdin[proc_id]), 1)
      self.assertIn("N: touch1", self.webadb.process_stdin[proc_id][0])

      self.platform.inject_input_events(
          "touch1",
          (
              TouchEvent(Point(100, 200), is_down=True),
              TouchEvent(Point(100, 200), is_down=False),
          ),
      )
      self.assertEqual(len(self.webadb.process_stdin[proc_id]), 2)
      self.assertIn("0003 0035 0100", self.webadb.process_stdin[proc_id][1])
      self.assertIn("0003 0036 0200", self.webadb.process_stdin[proc_id][1])

      self.platform.teardown_virtual_devices()
      self.assertIn(proc_id, self.webadb.closed_stdin_processes)
      self.assertEqual(self.platform._virtual_devices, {})

  @override
  def test_root_usb_and_noop_when_already_root(self) -> None:
    with mock.patch.object(self.webadb, "root") as mock_root:
      self.expect_sh("id", result="uid=0(root) gid=0(root)")
      self.adb.root()
      mock_root.assert_not_called()

      self.expect_sh("id", result="uid=2000(shell) gid=2000(shell)")
      self.adb.root()
      mock_root.assert_called_once()

  @override
  def test_unroot_usb_and_noop_when_not_root(self) -> None:
    with mock.patch.object(self.webadb, "unroot") as mock_unroot:
      self.expect_sh("id", result="uid=2000(shell) gid=2000(shell)")
      self.adb.unroot()
      mock_unroot.assert_not_called()

      self.expect_sh("id", result="uid=0(root) gid=0(root)")
      self.adb.unroot()
      mock_unroot.assert_called_once()

  @override
  def test_setup_unprovisioned_lazily_roots_and_dismisses_oobe(self) -> None:
    self.expect_sh("am get-current-user", result="10\n")
    self.expect_sh("settings get global device_provisioned", result="0\n")
    self.expect_sh("id", result="uid=2000(shell) gid=2000(shell)")
    self.expect_sh("getprop ro.build.type", result="userdebug")
    self.expect_sh("id", result="uid=2000(shell) gid=2000(shell)")
    self.expect_sh("id", result="uid=0(root) gid=0(root)")
    self.expect_sh("am start -a com.android.setupwizard.FOUR_CORNER_EXIT")
    self.expect_sh("settings get global device_provisioned", result="1\n")
    with (
        mock.patch.object(self.webadb, "root") as mock_root,
        mock.patch.object(self.platform, "sleep"),
    ):
      self.platform.setup()
      mock_root.assert_called_once()

  @override
  def test_setup_unprovisioned_root_failure_skips_oobe(self) -> None:
    self.expect_sh("am get-current-user", result="10\n")
    self.expect_sh("settings get global device_provisioned", result="0\n")
    self.expect_sh("id", result="uid=2000(shell) gid=2000(shell)")
    self.expect_sh("getprop ro.build.type", result="userdebug")
    self.expect_sh("id", result="uid=2000(shell) gid=2000(shell)")
    self.expect_sh("id", result="uid=2000(shell) gid=2000(shell)")
    with (
        mock.patch.object(self.webadb, "root") as mock_root,
        self.assertLogs(level="WARNING") as cm,
    ):
      self.platform.setup()
      mock_root.assert_called_once()
    self.assertTrue(
        any("did not acquire root privileges" in msg for msg in cm.output))

  @override
  def test_setup_skips_oobe_bypass_when_disabled(self) -> None:
    platform = PyodideAndroidAdbPlatform(
        host_platform=self.host_platform,
        device_identifier=self.DEVICE_ID,
        adb=self.adb,
        bypass_oobe=False)
    self.assertFalse(platform.bypass_oobe)
    self.expect_sh("am get-current-user", result="10\n")
    platform.setup()


class PyodideStreamingPopenTest(CrossbenchFakeFsTestCase):
  __test__ = True

  def setUp(self) -> None:
    super().setUp()
    self.webadb = MockWebAdb()
    self.platform = PyodidePlatform(webadb=self.webadb)
    self.android_platform = PyodideAndroidAdbPlatform(
        host_platform=self.platform,
        device_identifier="mock-serial-123",
        webadb=self.webadb,
    )

  def test_poll_running_and_complete(self) -> None:
    log_file = io.StringIO()
    proc = PyodideStreamingPopen(
        self.android_platform,
        proc_id=101,
        cmd="echo hello",
        local_log_file=log_file,
    )
    self.webadb.process_logs[101] = [
        json.dumps({
            "text": "line1\n",
            "nextOffset": 1,
            "isExited": False,
        }),
        json.dumps({
            "text": "line2\n",
            "nextOffset": 2,
            "isExited": True,
            "exitCode": 0,
        }),
    ]
    self.assertIsNone(proc.poll())
    self.assertEqual(log_file.getvalue(), "line1\n")
    self.assertEqual(proc.poll(), 0)
    self.assertEqual(proc.returncode, 0)
    self.assertEqual(proc.wait(), 0)
    self.assertEqual(log_file.getvalue(), "line1\nline2\n")

  def test_poll_error_exit_code(self) -> None:
    proc = PyodideStreamingPopen(
        self.android_platform,
        proc_id=101,
        cmd="failing_cmd",
    )
    self.webadb.process_logs[101] = [
        json.dumps({
            "text": "err\n",
            "nextOffset": 1,
            "isExited": True,
            "exitCode": 42,
        }),
    ]
    self.assertEqual(proc.poll(), 42)
    self.assertEqual(proc.returncode, 42)
    self.assertEqual(proc.wait(), 42)

  def test_kill(self) -> None:
    proc = PyodideStreamingPopen(
        self.android_platform,
        proc_id=101,
        cmd="sleep 100",
    )
    self.assertIsNone(proc.poll())
    proc.kill()
    self.assertIn(101, self.webadb.killed_processes)
    self.assertEqual(proc.returncode, -9)
    self.assertEqual(proc.poll(), -9)
    self.assertEqual(proc.wait(), -9)

  def test_terminate(self) -> None:
    proc = PyodideStreamingPopen(
        self.android_platform,
        proc_id=101,
        cmd="sleep 100",
    )
    self.assertIsNone(proc.poll())
    proc.terminate()
    self.assertIn(101, self.webadb.killed_processes)
    self.assertEqual(proc.returncode, -15)
    self.assertEqual(proc.poll(), -15)
    self.assertEqual(proc.wait(), -15)

  def test_send_signal(self) -> None:
    proc = PyodideStreamingPopen(
        self.android_platform,
        proc_id=101,
        cmd="sleep 100",
    )
    proc.send_signal(2)
    self.assertIn(101, self.webadb.killed_processes)
    self.assertEqual(proc.returncode, -2)

  def test_kill_already_exited(self) -> None:
    proc = PyodideStreamingPopen(
        self.android_platform,
        proc_id=101,
        cmd="exit_with_error",
    )
    self.webadb.process_logs[101] = [
        json.dumps({
            "text": "",
            "nextOffset": 1,
            "isExited": True,
            "exitCode": 1,
        }),
    ]
    self.assertEqual(proc.poll(), 1)
    self.webadb.killed_processes.clear()
    proc.kill()
    self.assertEqual(proc.returncode, 1)
    self.assertNotIn(101, self.webadb.killed_processes)

  def test_platform_popen(self) -> None:
    proc = self.android_platform.popen("cat", "/dev/null")
    self.assertIsInstance(proc, PyodideStreamingPopen)
    self.assertIn("cat /dev/null", self.webadb.spawned_processes)
    proc.kill()
    self.assertEqual(proc.returncode, -9)

  def test_stdin_pipe_write_and_close(self) -> None:
    proc = self.android_platform.popen("uinput", "-", stdin=subprocess.PIPE)
    self.assertIsNotNone(proc.stdin)
    assert proc.stdin is not None
    self.assertTrue(proc.stdin.writable())
    self.assertEqual(proc.stdin.write(b""), 0)
    self.assertEqual(proc.stdin.write(b"N: touch1\n"), 10)
    proc.stdin.flush()
    self.assertEqual(self.webadb.process_stdin[proc.pid], ["N: touch1\n"])
    proc.stdin.close()
    self.assertIn(proc.pid, self.webadb.closed_stdin_processes)
    with self.assertRaises(ValueError):
      proc.stdin.write(b"more")
    with self.assertRaises(ValueError):
      proc.stdin.flush()


del AndroidAdbMockPlatformTest, LocalLinuxMockPlatformTestCase

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
