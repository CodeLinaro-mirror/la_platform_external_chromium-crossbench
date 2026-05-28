# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import unittest
from unittest import mock

from crossbench.probes.netlog import NetLogCaptureMode, NetLogProbe, \
    NetLogProbeContext
from crossbench.probes.probe_error import ProbeIncompatibleBrowser, \
    ProbeValidationError
from tests import test_helper


class NetLogProbeTestCase(unittest.TestCase):

  def test_parse_config(self) -> None:
    probe = NetLogProbe.parse_dict({})
    self.assertEqual(probe.capture_mode, NetLogCaptureMode.DEFAULT)

    probe = NetLogProbe.parse_dict({"capture_mode": "Everything"})
    self.assertEqual(probe.capture_mode, NetLogCaptureMode.EVERYTHING)

    probe = NetLogProbe.parse_dict({"capture_mode": "Normal"})
    self.assertEqual(probe.capture_mode, NetLogCaptureMode.DEFAULT)

  def test_parse_str_default_argument(self) -> None:
    probe = NetLogProbe.parse_str("all")
    self.assertEqual(probe.capture_mode, NetLogCaptureMode.EVERYTHING)

    probe = NetLogProbe.parse_str("normal")
    self.assertEqual(probe.capture_mode, NetLogCaptureMode.DEFAULT)

    probe = NetLogProbe.parse_str("Everything")
    self.assertEqual(probe.capture_mode, NetLogCaptureMode.EVERYTHING)

  def test_validate_browser_incompatible(self) -> None:
    probe = NetLogProbe()
    browser = mock.MagicMock()
    browser.attributes.return_value.is_chromium_based = False
    env = mock.MagicMock()
    with self.assertRaises(ProbeIncompatibleBrowser):
      probe.validate_browser(env, browser)

  def test_validate_browser_conflicting_flags(self) -> None:
    probe = NetLogProbe()
    browser = mock.MagicMock()
    browser.attributes.return_value.is_chromium_based = True
    env = mock.MagicMock()

    browser.flags = {"--log-net-log": "/tmp/test.json"}
    with self.assertRaises(ProbeValidationError):
      probe.validate_browser(env, browser)

    browser.flags = {"--net-log-capture-mode": "Everything"}
    with self.assertRaises(ProbeValidationError):
      probe.validate_browser(env, browser)

  def test_setup(self) -> None:
    probe = NetLogProbe(capture_mode=NetLogCaptureMode.DEFAULT)
    run = mock.MagicMock()
    run.get_default_probe_result_path.return_value = pathlib.Path(
        "test_netlog.json")
    extra_flags: dict[str, str] = {}
    run.session.extra_flags = extra_flags
    context = NetLogProbeContext(probe, run)
    context.setup()
    self.assertEqual(extra_flags["--log-net-log"], str(context.result_path))
    self.assertEqual(extra_flags["--net-log-capture-mode"], "Default")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
