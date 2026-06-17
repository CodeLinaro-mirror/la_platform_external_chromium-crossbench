# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt
from unittest import mock

from crossbench import path as pth
from crossbench.probes.bits import BitsProbe
from crossbench.probes.probe import ProbeIncompatibleBrowser
from crossbench.probes.results import EmptyProbeResult
from tests import test_helper
from tests.crossbench.probes.helper import BaseProbeTestCase


class BitsProbeTestCase(BaseProbeTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.bits_path = pth.LocalPath(self.platform.default_tmp_dir) / "bits"
    self.fs.create_file(self.bits_path)

  def test_bits_probe_parsing_valid(self) -> None:
    probe = BitsProbe.parse_dict({
        "bits_path": str(self.bits_path),
        "bits_out": "run_id",
        "duration": "1s"
    })
    self.assertEqual(probe.bits_path, self.bits_path)
    self.assertEqual(probe.bits_out, "run_id")
    self.assertEqual(probe.duration, dt.timedelta(seconds=1))

  def test_bits_probe_parsing_missing_path(self) -> None:
    with self.assertRaises(argparse.ArgumentTypeError):
      BitsProbe.parse_dict({"bits_out": "run_id"})

  def test_bits_probe_parsing_zero_duration(self) -> None:
    with self.assertRaises(argparse.ArgumentTypeError):
      BitsProbe.parse_dict({
          "bits_path": str(self.bits_path),
          "bits_out": "run_id",
          "duration": "0s"
      })

  def test_bits_probe_parsing_subsecond_duration(self) -> None:
    with self.assertRaises(ValueError):
      BitsProbe.parse_dict({
          "bits_path": str(self.bits_path),
          "bits_out": "run_id",
          "duration": "500ms"
      })

  def test_bits_probe_parsing_negative_duration(self) -> None:
    with self.assertRaises(argparse.ArgumentTypeError):
      BitsProbe.parse_dict({
          "bits_path": str(self.bits_path),
          "bits_out": "run_id",
          "duration": "-5s"
      })

  def test_bits_probe_parsing_default_duration(self) -> None:
    probe = BitsProbe.parse_dict({
        "bits_path": str(self.bits_path),
        "bits_out": "test_run_id"
    })
    self.assertEqual(probe.bits_path, self.bits_path)
    self.assertEqual(probe.bits_out, "test_run_id")
    self.assertEqual(probe.duration, BitsProbe.DEFAULT_DURATION)

  def test_bits_probe_parsing_custom_duration(self) -> None:
    probe = BitsProbe.parse_dict({
        "bits_path": str(self.bits_path),
        "bits_out": "test_run_id",
        "duration": "2m"
    })
    self.assertEqual(probe.bits_path, self.bits_path)
    self.assertEqual(probe.bits_out, "test_run_id")
    self.assertEqual(probe.duration, dt.timedelta(minutes=2))
    self.assertEqual(probe.bits_device, "")

  def test_bits_probe_parsing_device(self) -> None:
    probe = BitsProbe.parse_dict({
        "bits_path": str(self.bits_path),
        "bits_out": "test_run_id",
        "device": "custom_id",
    })
    self.assertEqual(probe.bits_device, "custom_id")

  def test_bits_probe_parsing_device_empty(self) -> None:
    probe_empty = BitsProbe.parse_dict({
        "bits_path": str(self.bits_path),
        "bits_out": "test_run_id",
        "device": "",
    })
    self.assertEqual(probe_empty.bits_device, "")

  def test_validate_browser_incompatible(self) -> None:
    probe = BitsProbe(self.bits_path, "test_run_id")
    browser = self.magic_mock_browser
    browser.platform.is_android = False
    env = mock.MagicMock()
    with self.assertRaises(ProbeIncompatibleBrowser):
      probe.validate_browser(env, browser)

  def _check_probe_lifecycle(self, bits_device: str) -> None:
    probe = BitsProbe(
        self.bits_path,
        "test_run_id",
        bits_device=bits_device,
        duration=dt.timedelta(seconds=120),
    )
    run = self.mock_run()
    run.browser_session.browser.platform.serial_id = "serial"

    host_platform = run.browser_session.browser.host_platform
    host_platform.popen = mock.MagicMock()
    host_platform.sh = mock.MagicMock()

    context = probe.create_context(run)

    # 1. start() should be a no-op
    context.start()
    host_platform.popen.assert_not_called()

    # 2. start_story_run() should spawn BITS
    context.start_story_run()
    host_platform.popen.assert_called_once()
    call_args = host_platform.popen.call_args.args
    if bits_device:
      self.assertEqual(call_args[-2:], ("--device", bits_device))
    else:
      self.assertNotIn("--device", call_args)

    host_platform.popen.assert_called_once_with(
        self.bits_path,
        "--create",
        "test_run_id",
        "--duration",
        "120s",
        *(("--device", bits_device) if bits_device else []),
    )

    # 3. stop_story_run() should stop BITS
    context.stop_story_run()
    host_platform.sh.assert_called_once_with(
        self.bits_path,
        "--stop",
        "test_run_id",
    )

    # Reset mocks to verify that the final stop phase is a clean no-op
    host_platform.popen.reset_mock()
    host_platform.sh.reset_mock()

    # 4. stop() should be a no-op
    context.stop()
    host_platform.popen.assert_not_called()
    host_platform.sh.assert_not_called()

    self.assertIsInstance(context.teardown(), EmptyProbeResult)

  def test_probe_lifecycle(self) -> None:
    self._check_probe_lifecycle(bits_device="")

  def test_probe_lifecycle_with_device(self) -> None:
    self._check_probe_lifecycle(bits_device="device_id_123")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
