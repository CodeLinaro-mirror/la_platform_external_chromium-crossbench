# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import pathlib
from typing import cast
from unittest.mock import MagicMock, patch

from crossbench.action_runner.action.agent import AgentAction
from crossbench.action_runner.action.click import ClickAction
from crossbench.action_runner.action.mouse_move import MouseMoveAction
from crossbench.action_runner.action.scroll import ScrollAction
from crossbench.action_runner.action.swipe import SwipeAction
from crossbench.action_runner.action.text_input import TextInputAction
from crossbench.action_runner.action.wait import WaitAction
from crossbench.action_runner.action_runner import ActionRunner
from crossbench.action_runner.agent_driver import AgentDriver
from crossbench.action_runner.llm_client import AgentTurnResponse, \
    LlmConversationClient
from crossbench.benchmarks.loading.point import Point
from crossbench.browsers.settings import Settings
from crossbench.flags.base import Flags
from crossbench.runner.groups.session import BrowserSessionRunGroup
from tests import test_helper
from tests.crossbench.action_runner.action_runner_test_case import \
    ActionRunnerTestCase
from tests.crossbench.mock_browser import MockChromeStable
from tests.crossbench.mock_helper import LinuxMockPlatform
from tests.crossbench.runner.helper import MockRun, MockRunner


class AgentDriverTestCase(ActionRunnerTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.fs.create_file(
        "/usr/bin/google-chrome", contents="definitely a browser")
    self.root_dir = pathlib.Path("/tmp/results")
    self.fs.create_dir(self.root_dir)
    self.platform = LinuxMockPlatform(fake_fs=self.fs)
    self.mock_display_resolution = self.enterContext(
        patch.object(
            self.platform, "display_resolution", return_value=(1920, 1080)))
    self.enterContext(
        patch.object(
            self.platform, "screenshot", side_effect=self.platform.touch))
    self.browser = MockChromeStable(
        "mock browser", settings=Settings(platform=self.platform))
    self.runner = MockRunner(probes=[])
    self.session = BrowserSessionRunGroup(
        self.runner.env,
        self.runner.probes,
        self.browser,
        Flags(),
        1,
        self.root_dir,
        True,
        True,
    )
    self.mock_run: MockRun = MockRun(
        self.runner,
        self.session,
        "run 1",
    )
    self.fs.create_dir(self.mock_run.out_dir)
    self.action_runner = ActionRunner(self.mock_run)
    self.mock_run.action_runner = self.action_runner

  def test_agent_driver_executes_actions(self) -> None:
    mock_client = MagicMock(spec=LlmConversationClient)
    mock_client.send_turn.side_effect = [
        AgentTurnResponse(
            observation="Initial screen",
            thought="Wait briefly then finish",
            done=False,
            actions=(WaitAction.parse_dict({
                "action": "wait",
                "duration": "10ms",
            }),),
        ),
        AgentTurnResponse(
            observation="Wait completed",
            thought="Done exploring",
            done=True,
            actions=(),
        ),
    ]

    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Navigate to example.com",
        "max_steps": 5,
        "duration": "1m",
    })
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )
    driver.execute()

    self.assertEqual(mock_client.send_turn.call_count, 2)
    screenshots_dir = self.mock_run.out_dir / "agent_session" / "screenshots"
    self.assertTrue((screenshots_dir / "step_001.png").is_file())
    self.assertTrue((screenshots_dir / "step_002.png").is_file())

  def test_agent_driver_rejects_nested_agent_action(self) -> None:
    mock_client = MagicMock(spec=LlmConversationClient)
    mock_client.send_turn.side_effect = [
        AgentTurnResponse(
            observation="Initial screen",
            thought="Attempt nested agent",
            done=False,
            actions=(AgentAction.parse_dict({
                "action": "agent",
                "prompt": "Nested",
                "max_steps": 1,
                "duration": "10s",
            }),),
        ),
        AgentTurnResponse(
            observation="Rejected",
            thought="Done",
            done=True,
            actions=(),
        ),
    ]
    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Outer agent",
        "max_steps": 3,
        "duration": "1m",
    })
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )
    driver.execute()

    self.assertEqual(mock_client.send_turn.call_count, 2)
    second_turn_prompt = mock_client.send_turn.call_args_list[1].args[0]
    self.assertIn("Nested agent action is not allowed", second_turn_prompt)

  def test_agent_driver_isolates_sub_action_exceptions(self) -> None:
    mock_client = MagicMock(spec=LlmConversationClient)
    mock_client.send_turn.side_effect = [
        AgentTurnResponse(
            observation="Initial screen",
            thought="Try invalid click",
            done=False,
            actions=(ClickAction.parse_dict({
                "action": "click",
                "source": "touch",
                "pos": {
                    "x": 100,
                    "y": 100,
                },
            }),),
        ),
        AgentTurnResponse(
            observation="Click failed, finishing",
            thought="Done",
            done=True,
            actions=(),
        ),
    ]

    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Navigate to example.com",
        "max_steps": 5,
        "duration": "1m",
    })
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )
    with (
        self.assertLogs(level="DEBUG") as captured_logs,
        patch.object(
            self.action_runner,
            "click_touch",
            side_effect=RuntimeError(
                "Simulated click failure\nExtra debug detail line"),
        ),
    ):
      driver.execute()

    self.assertTrue(self.mock_run.exceptions.is_success)
    second_turn_prompt = mock_client.send_turn.call_args_list[1].args[0]
    self.assertIn("failed after", second_turn_prompt)
    self.assertIn("RuntimeError: Simulated click failure", second_turn_prompt)
    self.assertNotIn("Extra debug detail line", second_turn_prompt)
    self.assertTrue(
        any("Extra debug detail line" in msg for msg in captured_logs.output))

  def test_agent_driver_ignores_done_when_stop_on_done_is_false(self) -> None:
    mock_client = MagicMock(spec=LlmConversationClient)
    mock_client.send_turn.side_effect = [
        AgentTurnResponse(
            observation="Step 1",
            thought="Try to finish early",
            done=True,
            actions=(),
        ),
        AgentTurnResponse(
            observation="Step 2",
            thought="Forced to continue",
            done=True,
            actions=(WaitAction.parse_dict({
                "action": "wait",
                "duration": "10ms",
            }),),
        ),
    ]
    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Keep running until max_steps",
        "max_steps": 2,
        "duration": "1m",
        "stop_on_done": False,
    })
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )
    driver.execute()

    self.assertEqual(mock_client.send_turn.call_count, 2)
    second_turn_prompt = mock_client.send_turn.call_args_list[1].args[0]
    self.assertIn("Early completion ('done': true) is disabled",
                  second_turn_prompt)

  def test_format_action_error_reports_browser_stopped_any_exception(
      self) -> None:
    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Handle browser stopped runtime error",
        "max_steps": 1,
        "duration": "1m",
    })
    self.browser._is_running = False
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=MagicMock(spec=LlmConversationClient),
    )
    formatted = driver._format_action_error(
        RuntimeError("Browser session inactive"))
    self.assertIn("RuntimeError: Browser session inactive", formatted)
    self.assertIn("Browser is not running", formatted)

  def test_execute_turn_actions_catches_assertion_error_when_browser_stopped(
      self) -> None:
    mock_client = MagicMock(spec=LlmConversationClient)
    mock_client.send_turn.side_effect = [
        AgentTurnResponse(
            observation="Step 1",
            thought="Try scroll while browser is stopped",
            done=False,
            actions=(ScrollAction.parse_dict({
                "action": "scroll",
                "source": "touch",
                "distance": 400,
            }),),
        ),
        AgentTurnResponse(
            observation="Step 2",
            thought="Finish",
            done=True,
            actions=(),
        ),
    ]
    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Handle browser stopped assertion",
        "max_steps": 2,
        "duration": "1m",
    })
    self.browser._is_running = False
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )
    with patch.object(self.action_runner, "scroll", side_effect=AssertionError):
      driver.execute()

    self.assertEqual(mock_client.send_turn.call_count, 2)
    second_turn_prompt = mock_client.send_turn.call_args_list[1].args[0]
    self.assertIn("Browser is not running", second_turn_prompt)

  def test_agent_driver_scales_normalized_coordinates(self) -> None:
    mock_client = MagicMock(spec=LlmConversationClient)
    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Test coordinate scaling",
        "max_steps": 1,
        "duration": "1m",
    })
    self.mock_display_resolution.return_value = (2880, 1800)
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )

    scaled_click = cast(
        ClickAction,
        driver.prepare_sub_action(
            ClickAction.parse_dict({
                "action": "click",
                "source": "touch",
                "pos": {
                    "x": 500,
                    "y": 500,
                },
            })))
    assert scaled_click.position.coordinates is not None
    self.assertEqual(scaled_click.position.coordinates.x, 1440)
    self.assertEqual(scaled_click.position.coordinates.y, 900)

    scaled_swipe = cast(
        SwipeAction,
        driver.prepare_sub_action(
            SwipeAction.parse_dict({
                "action": "swipe",
                "start_x": 250,
                "start_y": 800,
                "end_x": 750,
                "end_y": 200,
                "duration": "400ms",
            })))
    self.assertEqual(scaled_swipe.start_x, 720)
    self.assertEqual(scaled_swipe.start_y, 1440)
    self.assertEqual(scaled_swipe.end_x, 2160)
    self.assertEqual(scaled_swipe.end_y, 360)

    scaled_mouse_move = cast(
        MouseMoveAction,
        driver.prepare_sub_action(
            MouseMoveAction.parse_dict({
                "action": "mouse_move",
                "waypoints": [
                    {
                        "x": 500,
                        "y": 500,
                    },
                    {
                        "x": 550,
                        "y": 500,
                    },
                    {
                        "x": 450,
                        "y": 500,
                    },
                ],
                "duration": "240ms",
            })))
    self.assertEqual(
        scaled_mouse_move.waypoints,
        (
            Point(1440, 900),
            Point(1584, 900),
            Point(1296, 900),
        ),
    )

  def test_agent_driver_enforces_realistic_typing_duration(self) -> None:
    mock_client = MagicMock(spec=LlmConversationClient)
    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Test typing duration",
        "max_steps": 1,
        "duration": "1m",
    })
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )

    scaled_typing_no_dur = cast(
        TextInputAction,
        driver.prepare_sub_action(
            TextInputAction.parse_dict({
                "action": "text_input",
                "source": "keyboard",
                "text": "hello world",
            })))
    self.assertEqual(scaled_typing_no_dur.duration,
                     dt.timedelta(milliseconds=1100))

    scaled_typing_too_fast = cast(
        TextInputAction,
        driver.prepare_sub_action(
            TextInputAction.parse_dict({
                "action": "text_input",
                "source": "keyboard",
                "text": "hello world",
                "duration": "200ms",
            })))
    self.assertEqual(scaled_typing_too_fast.duration,
                     dt.timedelta(milliseconds=1100))

    scaled_typing_slow_enough = cast(
        TextInputAction,
        driver.prepare_sub_action(
            TextInputAction.parse_dict({
                "action": "text_input",
                "source": "keyboard",
                "text": "hi",
                "duration": "1s",
            })))
    self.assertEqual(scaled_typing_slow_enough.duration,
                     dt.timedelta(seconds=1))

  def test_collect_environment_context_includes_active_tasks(self) -> None:
    mock_client = MagicMock(spec=LlmConversationClient)
    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Check active tasks",
        "max_steps": 1,
        "duration": "1m",
    })
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )
    self.assertEqual(driver._collect_environment_context(), "")
    with patch.object(
        self.platform,
        "get_active_tasks",
        return_value=["com.google.android.calculator", "com.dropbox.android"],
    ):
      self.assertEqual(
          driver._collect_environment_context(),
          "Active tasks (2 total):\n"
          "  - com.google.android.calculator\n"
          "  - com.dropbox.android",
      )


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
