# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import pathlib
from unittest import mock

from crossbench.action_runner.action.text_input import TextInputAction
from crossbench.action_runner.input_events import InputEvent, KeyEvent, \
    WaitEvent
from crossbench.action_runner.unified_input_action_runner import \
    UnifiedInputActionRunner
from crossbench.benchmarks.loading.input_source import InputSource
from crossbench.browsers.settings import Settings
from crossbench.flags.base import Flags
from crossbench.runner.groups.session import BrowserSessionRunGroup
from tests import test_helper
from tests.crossbench.action_runner.action_runner_test_case import \
    ActionRunnerTestCase
from tests.crossbench.mock_browser import MockChromeStable
from tests.crossbench.mock_helper import LinuxMockPlatform
from tests.crossbench.runner.helper import MockRun, MockRunner


class UnifiedInputActionRunnerTestCase(ActionRunnerTestCase):
  __test__ = True

  def setUp(self) -> None:
    super().setUp()
    self.platform = LinuxMockPlatform()
    self.fs.create_file("/usr/bin/google-chrome", contents="chrome_mock")
    self.browser = MockChromeStable(
        "mock browser", settings=Settings(platform=self.platform))
    self.runner = MockRunner()
    self.session = BrowserSessionRunGroup(self.runner.env, self.runner.probes,
                                          self.browser, Flags(), 1,
                                          pathlib.Path(), True, True)
    self.mock_run = MockRun(self.runner, self.session, "run 1")
    self.action_runner = UnifiedInputActionRunner(self.mock_run)
    self.mock_run.action_runner = self.action_runner

    # Mock inject_input_events on the existing platform directly
    self.inject_events_mock = mock.MagicMock()
    self.action_runner.browser_platform.inject_input_events = \
      self.inject_events_mock

  def run_action(self, action) -> None:
    action.run_with(self.action_runner)

  def assert_input_events_injected(self,
                                   expected_events: list[InputEvent]) -> None:
    self.inject_events_mock.assert_called_once()
    actual_events = self.inject_events_mock.call_args[0][0]
    self.assertListEqual(actual_events, expected_events)

  def test_text_input_text_zero_duration(self):
    text_input_action = TextInputAction(InputSource.KEYBOARD, dt.timedelta(),
                                        "a")
    self.run_action(text_input_action)

    self.assert_input_events_injected(
        [KeyEvent("KeyA", is_down=True),
         KeyEvent("KeyA", is_down=False)])

  def test_text_input_text_shift_modifier(self):
    text_input_action = TextInputAction(InputSource.KEYBOARD, dt.timedelta(),
                                        "A")
    self.run_action(text_input_action)

    self.assert_input_events_injected([
        KeyEvent("ShiftLeft", is_down=True),
        KeyEvent("KeyA", is_down=True),
        KeyEvent("KeyA", is_down=False),
        KeyEvent("ShiftLeft", is_down=False)
    ])

  def test_text_input_text_with_duration(self):
    # 2 seconds total for an action of length 4 ("abcd").
    # Each char has weight 10 (4 hold, 6 gap) -> 200ms hold, 300ms gap.
    text_input_action = TextInputAction(InputSource.KEYBOARD,
                                        dt.timedelta(seconds=2), "abcd")
    self.run_action(text_input_action)

    self.assert_input_events_injected([
        KeyEvent("KeyA", is_down=True),
        WaitEvent(duration=dt.timedelta(milliseconds=200)),
        KeyEvent("KeyA", is_down=False),
        WaitEvent(duration=dt.timedelta(milliseconds=300)),
        KeyEvent("KeyB", is_down=True),
        WaitEvent(duration=dt.timedelta(milliseconds=200)),
        KeyEvent("KeyB", is_down=False),
        WaitEvent(duration=dt.timedelta(milliseconds=300)),
        KeyEvent("KeyC", is_down=True),
        WaitEvent(duration=dt.timedelta(milliseconds=200)),
        KeyEvent("KeyC", is_down=False),
        WaitEvent(duration=dt.timedelta(milliseconds=300)),
        KeyEvent("KeyD", is_down=True),
        WaitEvent(duration=dt.timedelta(milliseconds=200)),
        KeyEvent("KeyD", is_down=False),
        WaitEvent(duration=dt.timedelta(milliseconds=300)),
    ])

  def test_text_input_text_shift_with_duration(self):
    text_input_action = TextInputAction(InputSource.KEYBOARD,
                                        dt.timedelta(milliseconds=100), "A")
    self.run_action(text_input_action)

    self.assert_input_events_injected([
        KeyEvent("ShiftLeft", is_down=True),
        WaitEvent(duration=dt.timedelta(milliseconds=10)),
        KeyEvent("KeyA", is_down=True),
        WaitEvent(duration=dt.timedelta(milliseconds=30)),
        KeyEvent("KeyA", is_down=False),
        WaitEvent(duration=dt.timedelta(milliseconds=10)),
        KeyEvent("ShiftLeft", is_down=False),
        WaitEvent(duration=dt.timedelta(milliseconds=50)),
    ])

  def test_text_input_keyevent_zero_duration(self):
    text_input_action = TextInputAction(
        InputSource.KEYBOARD, dt.timedelta(), keyevent="Enter")
    self.run_action(text_input_action)

    self.assert_input_events_injected(
        [KeyEvent("Enter", is_down=True),
         KeyEvent("Enter", is_down=False)])

  def test_text_input_keyevent_with_duration(self):
    text_input_action = TextInputAction(
        InputSource.KEYBOARD, dt.timedelta(seconds=1), keyevent="Enter")
    self.run_action(text_input_action)

    self.assert_input_events_injected([
        KeyEvent("Enter", is_down=True),
        WaitEvent(duration=dt.timedelta(milliseconds=400)),
        KeyEvent("Enter", is_down=False),
        WaitEvent(duration=dt.timedelta(milliseconds=600)),
    ])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
