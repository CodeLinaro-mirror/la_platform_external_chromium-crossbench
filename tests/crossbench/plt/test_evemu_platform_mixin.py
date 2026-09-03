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
from crossbench.plt.evemu_platform_mixin import EvemuPlatformMixin
from tests import test_helper

if TYPE_CHECKING:
  from crossbench.plt.types import TupleCmdArgs


class MockEvemuPlatform(EvemuPlatformMixin):

  def __init__(self) -> None:
    super().__init__()
    self.mock_proc = mock.MagicMock()
    self.mock_proc.poll.return_value = None
    self.mock_proc.stdin = mock.MagicMock()
    self.popen_calls: list[tuple] = []

  def _get_evemu_device_cmd(self,
                            device_type: VirtualDeviceType) -> TupleCmdArgs:
    del device_type
    return ("mock-evemu", "-")

  def popen(self, *args, **kwargs) -> subprocess.Popen:
    self.popen_calls.append((args, kwargs))
    return self.mock_proc


class EvemuPlatformMixinTestCase(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    self.platform = MockEvemuPlatform()
    self.platform.setup_virtual_devices((VirtualDeviceConfig(
        name="test_kb", device_type=VirtualDeviceType.KEYBOARD),))

  def test_setup_virtual_devices(self) -> None:
    platform = MockEvemuPlatform()
    platform.setup_virtual_devices((VirtualDeviceConfig(
        name="kb1", device_type=VirtualDeviceType.KEYBOARD),))
    self.assertEqual(len(platform.popen_calls), 1)
    args, kwargs = platform.popen_calls[0]
    self.assertEqual(args, ("mock-evemu", "-"))
    self.assertEqual(kwargs, {"stdin": subprocess.PIPE})
    self.assertIn("kb1", platform._virtual_devices)
    self.assertIs(platform._virtual_devices["kb1"], platform.mock_proc)
    platform.mock_proc.stdin.write.assert_called_once()
    platform.mock_proc.stdin.flush.assert_called_once()

  def test_setup_virtual_devices_unsupported(self) -> None:
    platform = MockEvemuPlatform()
    unsupported_config = mock.MagicMock(spec=VirtualDeviceConfig)
    unsupported_config.device_type = "unsupported_device_type"
    unsupported_config.name = "touch1"

    with self.assertRaisesRegex(ValueError, "Unsupported virtual device type"):
      platform.setup_virtual_devices((unsupported_config,))

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

  def test_single_key(self) -> None:
    self.platform.inject_input_events("test_kb", [
        KeyEvent("KeyA", is_down=True),
    ])
    self.platform.mock_proc.stdin.write.assert_called_with(
        b"E: 0.000000 0001 001e 0001\nE: 0.000000 0000 0000 0000\n")
    self.platform.mock_proc.stdin.flush.assert_called()

  def test_key_with_wait(self) -> None:
    self.platform.inject_input_events(
        "test_kb",
        [
            KeyEvent("KeyA", is_down=True),
            WaitEvent(dt.timedelta(milliseconds=1500)),  # 1.5 seconds wait
            KeyEvent("KeyA", is_down=False),
        ])
    self.platform.mock_proc.stdin.write.assert_called_with(
        b"E: 0.000000 0001 001e 0001\n"
        b"E: 0.000000 0000 0000 0000\n"
        b"E: 1.500000 0001 001e 0000\n"
        b"E: 1.500000 0000 0000 0000\n")

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
