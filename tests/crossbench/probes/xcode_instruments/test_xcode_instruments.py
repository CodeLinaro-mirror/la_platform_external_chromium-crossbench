# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import enum
import io
import subprocess
from typing import Final
from unittest import mock

from crossbench import path as pth
from crossbench.exception import ArgumentTypeMultiException
from crossbench.plt.ios import IOSPlatform
from crossbench.plt.macos import MacOSPlatform
from crossbench.probes.probe_error import ProbeIncompatibleBrowser, \
    ProbeValidationError
from crossbench.probes.profiling.enum import TargetMode
from crossbench.probes.xcode_instruments.instrument_package import \
    InstrumentPackage
from crossbench.probes.xcode_instruments.recorder import XctraceRecorder
from crossbench.probes.xcode_instruments.xcode_instruments import \
    XcodeInstrumentsProbe
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase

_RECORDING_OUTPUT: Final[str] = ("Starting recording with the instrument.\n"
                                 "Ctrl-C to stop the recording\n")

_INSTRPKG: Final[str] = (
    "<package><instrument><title>na</title></instrument></package>")


class TargetPlatform(enum.Enum):
  MACOS = "macOS"
  IOS = "iOS"
  OTHER = "other"


def _mock_browser(target_platform: TargetPlatform, host_is_macos: bool,
                  has_xctrace: bool) -> mock.Mock:
  browser = mock.Mock()
  if target_platform == TargetPlatform.MACOS:
    browser.platform = mock.Mock(spec=MacOSPlatform)
  elif target_platform == TargetPlatform.IOS:
    browser.platform = mock.Mock(spec=IOSPlatform)
  browser.platform.is_macos = (target_platform == TargetPlatform.MACOS)
  browser.platform.is_ios = (target_platform == TargetPlatform.IOS)
  if host_is_macos:
    browser.host_platform = mock.Mock(spec=MacOSPlatform)
  browser.host_platform.is_macos = host_is_macos
  browser.host_platform.which.return_value = ("/usr/bin/xctrace"
                                              if has_xctrace else None)
  return browser


class XcodeInstrumentsProbeTestCase(CrossbenchFakeFsTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.instrument = pth.LocalPath("/tmp/counters.instrpkg")
    self.fs.create_file(self.instrument, contents=_INSTRPKG)
    self.instrument = self.instrument.resolve()

  def test_default_target(self):
    probe = XcodeInstrumentsProbe(instrument=self.instrument)
    self.assertEqual(probe.target, TargetMode.SYSTEM_WIDE)

  def test_instrument_is_required(self):
    with self.assertRaises(ArgumentTypeMultiException):
      XcodeInstrumentsProbe.parse_dict({})

  def test_parse_dict(self):
    probe = XcodeInstrumentsProbe.parse_dict({
        "instrument": str(self.instrument),
        "target": "browser_app_only",
    })
    self.assertEqual(probe.instrument, self.instrument)
    self.assertEqual(probe.target, TargetMode.BROWSER_APP_ONLY)

  def test_parse_str(self):
    probe = XcodeInstrumentsProbe.parse_str(str(self.instrument))
    self.assertEqual(probe.instrument, self.instrument)
    self.assertEqual(probe.target, TargetMode.SYSTEM_WIDE)

  def test_parse_dict_missing_instrument_file(self):
    with self.assertRaises(ArgumentTypeMultiException):
      XcodeInstrumentsProbe.parse_dict({"instrument": "/does/not/exist.xyz"})

  def test_parse_dict_invalid_instrument_file(self):
    invalid = pth.LocalPath("/tmp/invalid.instrpkg")
    self.fs.create_file(invalid, contents="<package/>")
    with self.assertRaises(ArgumentTypeMultiException):
      XcodeInstrumentsProbe.parse_dict({"instrument": str(invalid)})

  def test_key_differs_by_instrument(self):
    probe_a = XcodeInstrumentsProbe(instrument=self.instrument)
    other = pth.LocalPath("/tmp/other.instrpkg")
    self.fs.create_file(other)
    probe_b = XcodeInstrumentsProbe(instrument=other)
    self.assertNotEqual(probe_a.key, probe_b.key)

  def test_key_differs_by_target(self):
    probe_a = XcodeInstrumentsProbe(
        instrument=self.instrument, target=TargetMode.SYSTEM_WIDE)
    probe_b = XcodeInstrumentsProbe(
        instrument=self.instrument, target=TargetMode.BROWSER_APP_ONLY)
    self.assertNotEqual(probe_a.key, probe_b.key)

  def test_validate_macos_ok(self):
    probe = XcodeInstrumentsProbe(instrument=self.instrument)
    probe.validate_browser(
        mock.Mock(),
        _mock_browser(
            TargetPlatform.MACOS, host_is_macos=True, has_xctrace=True))

  def test_validate_ios_ok(self):
    probe = XcodeInstrumentsProbe(instrument=self.instrument)
    probe.validate_browser(
        mock.Mock(),
        _mock_browser(TargetPlatform.IOS, host_is_macos=True, has_xctrace=True))

  def test_validate_rejects_other_platform(self):
    probe = XcodeInstrumentsProbe(instrument=self.instrument)
    with self.assertRaisesRegex(ProbeIncompatibleBrowser, "(?i)macOS and iOS"):
      probe.validate_browser(
          mock.Mock(),
          _mock_browser(
              TargetPlatform.OTHER, host_is_macos=True, has_xctrace=True))

  def test_validate_rejects_non_macos_host(self):
    probe = XcodeInstrumentsProbe(instrument=self.instrument)
    with self.assertRaisesRegex(ProbeIncompatibleBrowser, "(?i)macOS host"):
      probe.validate_browser(
          mock.Mock(),
          _mock_browser(
              TargetPlatform.IOS, host_is_macos=False, has_xctrace=True))

  def test_validate_rejects_missing_xctrace(self):
    probe = XcodeInstrumentsProbe(instrument=self.instrument)
    with self.assertRaisesRegex(ProbeValidationError, "(?i)install Xcode"):
      probe.validate_browser(
          mock.Mock(),
          _mock_browser(
              TargetPlatform.MACOS, host_is_macos=True, has_xctrace=False))

  def test_validate_rejects_invalid_targets(self):
    browser = _mock_browser(
        TargetPlatform.MACOS, host_is_macos=True, has_xctrace=True)
    probe_auto = XcodeInstrumentsProbe(
        instrument=self.instrument, target=TargetMode.AUTO)
    with self.assertRaisesRegex(
        ProbeIncompatibleBrowser,
        f"(?i)Unsupported target mode: {TargetMode.AUTO}"):
      probe_auto.validate_browser(mock.Mock(), browser)

    probe_renderer_main = XcodeInstrumentsProbe(
        instrument=self.instrument, target=TargetMode.RENDERER_MAIN_ONLY)
    with self.assertRaisesRegex(
        ProbeIncompatibleBrowser,
        f"(?i)Unsupported target mode: {TargetMode.RENDERER_MAIN_ONLY}"):
      probe_renderer_main.validate_browser(mock.Mock(), browser)


class XcodeInstrumentsContextTestCase(CrossbenchFakeFsTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.instrument = pth.LocalPath("/tmp/counters.instrpkg")

  def _create_context(self, probe, browser):
    run = mock.Mock()
    run.browser = browser
    run.get_default_probe_result_path.return_value = pth.LocalPath(
        "/tmp/result")
    return probe.create_context(run)

  def test_setup_builds_package(self):
    probe = XcodeInstrumentsProbe(instrument=self.instrument)
    browser = _mock_browser(
        TargetPlatform.MACOS, host_is_macos=True, has_xctrace=True)
    context = self._create_context(probe, browser)
    package = InstrumentPackage(
        pth.LocalPath("/tmp/cache/counters.instrdst"), ("Counters",))
    with mock.patch.object(
        InstrumentPackage, "build", return_value=package) as build:
      context.setup()
    build.assert_called_once_with(browser.host_platform, self.instrument)
    self.assertIs(context._package, package)

  def test_get_attach_pid_system_wide(self):
    probe = XcodeInstrumentsProbe(
        instrument=self.instrument, target=TargetMode.SYSTEM_WIDE)
    browser = _mock_browser(
        TargetPlatform.MACOS, host_is_macos=True, has_xctrace=True)
    context = self._create_context(probe, browser)
    self.assertIsNone(context.get_attach_pid())

  def test_get_attach_pid_browser_app_only(self):
    probe = XcodeInstrumentsProbe(
        instrument=self.instrument, target=TargetMode.BROWSER_APP_ONLY)
    browser = _mock_browser(
        TargetPlatform.MACOS, host_is_macos=True, has_xctrace=True)
    browser.pid = 1234
    context = self._create_context(probe, browser)
    self.assertEqual(context.get_attach_pid(), 1234)

    browser.pid = None
    context = self._create_context(probe, browser)
    with self.assertRaisesRegex(ValueError, "(?i)browser-app tracing"):
      context.get_attach_pid()

  def test_get_attach_pid_renderer_process_only(self):
    probe = XcodeInstrumentsProbe(
        instrument=self.instrument, target=TargetMode.RENDERER_PROCESS_ONLY)
    browser = _mock_browser(
        TargetPlatform.MACOS, host_is_macos=True, has_xctrace=True)
    browser.get_renderer_pid.return_value = 5678
    context = self._create_context(probe, browser)
    self.assertEqual(context.get_attach_pid(), 5678)

    browser.get_renderer_pid.return_value = None
    context = self._create_context(probe, browser)
    with self.assertRaisesRegex(ValueError, "(?i)renderer-only tracing"):
      context.get_attach_pid()


class XctraceRecorderTestCase(CrossbenchFakeFsTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.package = InstrumentPackage(
        pth.LocalPath("/tmp/counters.instrdst"), ("Counters", "Signposts"))
    self.output_path = pth.LocalPath("/tmp/result/trace.trace")
    self.fs.create_dir(self.output_path.parent)

  def test_request_stop_signals_sigint(self):
    mock_platform = mock.Mock()
    mock_platform.is_file.return_value = True
    mock_platform.exists.return_value = True
    mock_process = mock.Mock()
    mock_process.poll.return_value = None
    mock_process.stdout = io.StringIO(_RECORDING_OUTPUT)
    mock_platform.popen.return_value = mock_process
    mock_platform.signals.SIGINT = 2

    recorder = XctraceRecorder(mock_platform, self.package, self.output_path)
    recorder.start()
    recorder.request_stop()
    mock_platform.send_signal.assert_called_once_with(mock_process, 2)

  def test_finalize_waits_and_unregisters(self):
    mock_platform = mock.Mock()
    mock_platform.is_file.return_value = True
    mock_platform.exists.return_value = True
    mock_process = mock.Mock()
    mock_process.poll.return_value = None
    mock_process.stdout = io.StringIO(_RECORDING_OUTPUT)
    mock_platform.popen.return_value = mock_process
    mock_platform.signals.SIGINT = 2

    recorder = XctraceRecorder(mock_platform, self.package, self.output_path)
    recorder.start()
    recorder.finalize()
    mock_platform.terminate_gracefully.assert_called_once()
    self.assertFalse(recorder.is_recording)

  def test_start_waits_for_recording_marker(self):
    mock_platform = mock.Mock()
    mock_platform.is_file.return_value = True
    mock_process = mock.Mock()
    mock_process.poll.return_value = None
    mock_process.stdout = io.StringIO(_RECORDING_OUTPUT)
    mock_platform.popen.return_value = mock_process

    recorder = XctraceRecorder(mock_platform, self.package, self.output_path)
    recorder.start()
    self.assertTrue(recorder.is_recording)
    self.assertEqual(mock_platform.popen.call_args.args,
                     ("xctrace", "record", "--package", self.package.path,
                      "--instrument", "Counters", "--instrument", "Signposts",
                      "--all-processes", "--output", self.output_path))
    popen_kwargs = mock_platform.popen.call_args.kwargs
    self.assertEqual(popen_kwargs["stdout"], subprocess.PIPE)
    self.assertEqual(popen_kwargs["stderr"], subprocess.STDOUT)

  def test_start_fails_if_xctrace_exits(self):
    mock_platform = mock.Mock()
    mock_platform.is_file.return_value = True
    mock_process = mock.Mock()
    mock_process.poll.return_value = 1
    mock_process.stdout = io.StringIO("Error: invalid package\n")
    mock_platform.popen.return_value = mock_process

    recorder = XctraceRecorder(mock_platform, self.package, self.output_path)
    with self.assertRaisesRegex(ValueError, "Could not start xctrace"):
      recorder.start()


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
