# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import subprocess
import unittest
from typing import TYPE_CHECKING
from unittest import mock

from crossbench.action_runner.config import VirtualDeviceConfig, \
    VirtualDeviceType
from crossbench.action_runner.input_events import InputEvent, KeyEvent, \
    WaitEvent
from crossbench.benchmarks.loading.input_source import InputSource
from crossbench.plt.evemu_platform_mixin import _INPUT_DRAIN_BUFFER, \
    _INPUT_LEAD_BUFFER, EvemuPlatformMixin
from tests import test_helper
from tests.crossbench.mock_helper import LinuxMockPlatform

if TYPE_CHECKING:
  from crossbench.plt.types import TupleCmdArgs


class MockEvemuPlatform(EvemuPlatformMixin, LinuxMockPlatform):

  def __init__(self) -> None:
    super().__init__()
    self.mock_proc = mock.MagicMock()
    self.mock_proc.poll.return_value = None
    self.mock_proc.stdin = mock.MagicMock()
    self.popen_calls: list[tuple] = []
    self.sleep_calls: list[float | dt.timedelta] = []

  def _get_evemu_device_cmd(self,
                            device_type: VirtualDeviceType) -> TupleCmdArgs:
    del device_type
    return ("mock-evemu", "-")

  def popen(self, *args, **kwargs) -> subprocess.Popen:
    self.popen_calls.append((args, kwargs))
    return self.mock_proc

  def sleep(self, seconds: float | dt.timedelta) -> None:
    self.sleep_calls.append(seconds)


class EvemuPlatformMixinTestCase(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    self.platform = MockEvemuPlatform()
    with mock.patch("time.monotonic", return_value=100.0):
      self.platform.setup_virtual_devices((VirtualDeviceConfig(
          name="test_kb", device_type=VirtualDeviceType.KEYBOARD),))
    self.platform.sleep_calls.clear()

  def test_setup_virtual_devices(self) -> None:
    platform = MockEvemuPlatform()
    platform.setup_virtual_devices((VirtualDeviceConfig(
        name="kb1", device_type=VirtualDeviceType.KEYBOARD),))
    self.assertEqual(len(platform.popen_calls), 1)
    args, kwargs = platform.popen_calls[0]
    self.assertEqual(args, ("mock-evemu", "-"))
    self.assertEqual(kwargs, {"stdin": subprocess.PIPE})
    self.assertIn("kb1", platform._virtual_devices)
    self.assertIs(platform._virtual_devices["kb1"].proc, platform.mock_proc)
    platform.mock_proc.stdin.write.assert_called_once()
    platform.mock_proc.stdin.flush.assert_called_once()

  def test_teardown_virtual_devices(self) -> None:
    self.assertIn("test_kb", self.platform._virtual_devices)
    self.platform.teardown_virtual_devices()
    self.assertEqual(self.platform._virtual_devices, {})
    self.platform.mock_proc.stdin.close.assert_called_once()
    self.platform.mock_proc.wait.assert_called_once_with(timeout=2)

  def test_setup_virtual_devices_unsupported(self) -> None:
    platform = MockEvemuPlatform()
    unsupported_config = mock.MagicMock(spec=VirtualDeviceConfig)
    unsupported_config.device_type = "unsupported_device_type"
    unsupported_config.name = "touch1"

    with self.assertRaisesRegex(ValueError, "Unsupported virtual device type"):
      platform.setup_virtual_devices((unsupported_config,))

  def test_get_default_device(self) -> None:
    platform = MockEvemuPlatform()
    self.assertIsNone(platform.get_default_device(InputSource.KEYBOARD))
    self.assertIsNone(platform.get_default_device(InputSource.TOUCH))
    platform.setup_virtual_devices((VirtualDeviceConfig(
        name="kb1", device_type=VirtualDeviceType.KEYBOARD),))
    self.assertEqual(platform.get_default_device(InputSource.KEYBOARD), "kb1")
    self.assertIsNone(platform.get_default_device(InputSource.TOUCH))

  def test_execute_evemu_script(self) -> None:
    self.platform._execute_evemu_script("test_kb",
                                        "E: 0.000000 0001 001e 0001\n")
    self.platform.mock_proc.stdin.write.assert_called_with(
        b"E: 0.000000 0001 001e 0001\n")
    self.platform.mock_proc.stdin.flush.assert_called()

  def test_execute_evemu_script_uninitialized(self) -> None:
    with self.assertRaisesRegex(RuntimeError,
                                "Virtual device 'unknown' was not initialized"):
      self.platform._execute_evemu_script("unknown", "E: ...")

  @mock.patch("time.monotonic", return_value=100.5)
  def test_single_key(self, mock_monotonic) -> None:
    del mock_monotonic
    self.platform.inject_input_events("test_kb", [
        KeyEvent("KeyA", is_down=True),
    ])
    self.platform.mock_proc.stdin.write.assert_called_with(
        b"E: 0.200000 0001 001e 0001\nE: 0.200000 0000 0000 0000\n")
    self.platform.mock_proc.stdin.flush.assert_called()

  @mock.patch("time.monotonic", return_value=100.5)
  def test_key_with_wait(self, mock_monotonic) -> None:
    del mock_monotonic
    self.platform.inject_input_events(
        "test_kb",
        [
            KeyEvent("KeyA", is_down=True),
            WaitEvent(dt.timedelta(milliseconds=1500)),  # 1.5 seconds wait
            KeyEvent("KeyA", is_down=False),
        ])
    self.platform.mock_proc.stdin.write.assert_called_with(
        b"E: 0.200000 0001 001e 0001\n"
        b"E: 0.200000 0000 0000 0000\n"
        b"E: 1.700000 0001 001e 0000\n"
        b"E: 1.700000 0000 0000 0000\n")

  @mock.patch("time.monotonic")
  def test_consecutive_injections_monotonic_timestamps(self,
                                                       mock_monotonic) -> None:
    mock_monotonic.return_value = 100.5
    self.platform.inject_input_events("test_kb", [
        KeyEvent("KeyA", is_down=True),
        WaitEvent(dt.timedelta(milliseconds=500)),
        KeyEvent("KeyA", is_down=False),
    ])
    self.platform.mock_proc.stdin.write.assert_called_with(
        b"E: 0.200000 0001 001e 0001\n"
        b"E: 0.200000 0000 0000 0000\n"
        b"E: 0.700000 0001 001e 0000\n"
        b"E: 0.700000 0000 0000 0000\n")
    self.assertEqual(self.platform.sleep_calls, [
        dt.timedelta(milliseconds=500) + _INPUT_LEAD_BUFFER +
        _INPUT_DRAIN_BUFFER,
    ])

    mock_monotonic.return_value = 101.0
    self.platform.inject_input_events("test_kb", [
        KeyEvent("KeyB", is_down=True),
        WaitEvent(dt.timedelta(milliseconds=200)),
        KeyEvent("KeyB", is_down=False),
    ])
    self.platform.mock_proc.stdin.write.assert_called_with(
        b"E: 0.700000 0001 0030 0001\n"
        b"E: 0.700000 0000 0000 0000\n"
        b"E: 0.900000 0001 0030 0000\n"
        b"E: 0.900000 0000 0000 0000\n")
    self.assertEqual(self.platform.sleep_calls, [
        dt.timedelta(milliseconds=500) + _INPUT_LEAD_BUFFER +
        _INPUT_DRAIN_BUFFER,
        (dt.timedelta(milliseconds=200) + _INPUT_LEAD_BUFFER +
         _INPUT_DRAIN_BUFFER),
    ])

  @mock.patch("time.monotonic")
  def test_consecutive_injections_with_delay(self, mock_monotonic) -> None:
    mock_monotonic.return_value = 100.5
    self.platform.inject_input_events("test_kb", [
        KeyEvent("KeyA", is_down=True),
        WaitEvent(dt.timedelta(milliseconds=500)),
        KeyEvent("KeyA", is_down=False),
    ])
    self.platform.mock_proc.stdin.write.assert_called_with(
        b"E: 0.200000 0001 001e 0001\n"
        b"E: 0.200000 0000 0000 0000\n"
        b"E: 0.700000 0001 001e 0000\n"
        b"E: 0.700000 0000 0000 0000\n")

    # Simulate 5 seconds elapsed between injections
    mock_monotonic.return_value = 105.5
    self.platform.inject_input_events("test_kb", [
        KeyEvent("KeyB", is_down=True),
        WaitEvent(dt.timedelta(milliseconds=200)),
        KeyEvent("KeyB", is_down=False),
    ])
    self.platform.mock_proc.stdin.write.assert_called_with(
        b"E: 5.200000 0001 0030 0001\n"
        b"E: 5.200000 0000 0000 0000\n"
        b"E: 5.400000 0001 0030 0000\n"
        b"E: 5.400000 0000 0000 0000\n")
    self.assertEqual(self.platform.sleep_calls, [
        dt.timedelta(milliseconds=500) + _INPUT_LEAD_BUFFER +
        _INPUT_DRAIN_BUFFER,
        (dt.timedelta(milliseconds=200) + _INPUT_LEAD_BUFFER +
         _INPUT_DRAIN_BUFFER),
    ])

  def test_unsupported_key(self) -> None:
    with self.assertRaises(ValueError):
      self.platform.inject_input_events("test_kb", [
          KeyEvent("UnsupportedKey", is_down=True),
      ])

  def test_unsupported_event_type(self) -> None:
    with self.assertRaisesRegex(ValueError,
                                "Unsupported event type: InputEvent"):
      self.platform.inject_input_events("test_kb", [InputEvent()])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
