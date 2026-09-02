# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import unittest

from crossbench.action_runner.input_events import InputEvent, KeyEvent, \
    WaitEvent
from crossbench.plt.evemu_platform_mixin import EvemuPlatformMixin
from tests import test_helper


class MockEvemuPlatform(EvemuPlatformMixin):

  def __init__(self) -> None:
    self.script_calls: list[tuple[str, str]] = []

  def _execute_evemu_script(self, device_name: str, script: str) -> None:
    self.script_calls.append((device_name, script))


class EvemuPlatformMixinTestCase(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    self.platform = MockEvemuPlatform()

  def test_single_key(self) -> None:
    self.platform.inject_input_events("test_kb", [
        KeyEvent("KeyA", is_down=True),
    ])
    self.assertEqual(len(self.platform.script_calls), 1)
    device_name, script = self.platform.script_calls[0]
    self.assertEqual(device_name, "test_kb")
    # Should contain EV_KEY KEY_A (001e) value 1, and a SYN
    self.assertIn("E: 0.000000 0001 001e 0001", script)
    self.assertIn("E: 0.000000 0000 0000 0000", script)

  def test_key_with_wait(self) -> None:
    self.platform.inject_input_events(
        "test_kb",
        [
            KeyEvent("KeyA", is_down=True),
            WaitEvent(dt.timedelta(milliseconds=1500)),  # 1.5 seconds wait
            KeyEvent("KeyA", is_down=False),
        ])

    device_name, script = self.platform.script_calls[0]
    self.assertEqual(device_name, "test_kb")
    lines = script.strip().split("\n")
    self.assertEqual(len(lines), 4)

    # Initial down at 0.0s
    self.assertEqual(lines[0], "E: 0.000000 0001 001e 0001")
    self.assertEqual(lines[1], "E: 0.000000 0000 0000 0000")

    # Up at 1.500000s
    self.assertEqual(lines[2], "E: 1.500000 0001 001e 0000")
    self.assertEqual(lines[3], "E: 1.500000 0000 0000 0000")

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
