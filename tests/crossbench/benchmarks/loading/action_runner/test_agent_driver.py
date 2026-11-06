# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import json
import pathlib
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

from crossbench.action_runner.action.agent import AgentAction
from crossbench.action_runner.action.click import ClickAction
from crossbench.action_runner.action.mouse_move import MouseMoveAction
from crossbench.action_runner.action.scroll import ScrollAction
from crossbench.action_runner.action.swipe import SwipeAction
from crossbench.action_runner.action.text_input import TextInputAction
from crossbench.action_runner.action.wait import WaitAction
from crossbench.action_runner.action_runner import ActionRunner
from crossbench.action_runner.agent_driver import PROMPTS_DIR, \
    SYSTEM_INSTRUCTION_TEMPLATE_PATH, AgentDriver
from crossbench.action_runner.llm_client import AgentTurnResponse, \
    LlmConversationClient
from crossbench.benchmarks.loading.point import Point
from crossbench.browsers.settings import Settings
from crossbench.cli.config.secrets import Secrets
from crossbench.flags.base import Flags
from crossbench.plt.bin import Binaries
from crossbench.probes.cb_perfetto.perfetto import PerfettoProbe
from crossbench.runner.groups.session import BrowserSessionRunGroup
from tests import test_helper
from tests.crossbench.action_runner.action_runner_test_case import \
    ActionRunnerTestCase
from tests.crossbench.mock_browser import MockChromeStable
from tests.crossbench.mock_helper import LinuxMockPlatform
from tests.crossbench.runner.helper import MockRun, MockRunner

if TYPE_CHECKING:
  from crossbench.probes.probe import Probe


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
    episode_dir = self.mock_run.out_dir / "agent_episodes" / "episode_000"
    self.assertEqual(driver.episode_dir, episode_dir)
    screenshots_dir = episode_dir / "screenshots"
    self.assertTrue((screenshots_dir / "step_001.png").is_file())
    self.assertTrue((screenshots_dir / "step_002.png").is_file())

    episode_meta_file = episode_dir / "episode.json"
    replay_file = episode_dir / "replay_actions.hjson"
    transcript_file = episode_dir / "transcript.jsonl"
    self.assertTrue(episode_meta_file.is_file())
    self.assertTrue(replay_file.is_file())
    self.assertTrue(transcript_file.is_file())

    episode_meta = json.loads(episode_meta_file.read_text(encoding="utf-8"))
    self.assertEqual(episode_meta["episode_id"], "episode_000")
    self.assertEqual(episode_meta["episode_index"], 0)
    self.assertEqual(episode_meta["info_stack"], [])
    self.assertEqual(episode_meta["action"]["prompt"],
                     "Navigate to example.com")

    replay_data = json.loads(replay_file.read_text(encoding="utf-8"))
    self.assertEqual(len(replay_data["actions"]), 1)
    self.assertEqual(replay_data["actions"][0]["type"], "wait")

    transcript_lines = (
        transcript_file.read_text(encoding="utf-8").strip().splitlines())
    self.assertEqual(len(transcript_lines), 2)
    first_entry = json.loads(transcript_lines[0])
    self.assertEqual(first_entry["episode_id"], "episode_000")
    self.assertEqual(first_entry["step"], 1)
    self.assertEqual(first_entry["thought"], "Wait briefly then finish")

  def test_agent_driver_isolates_multiple_episodes(self) -> None:
    first_client = MagicMock(spec=LlmConversationClient)
    first_client.send_turn.side_effect = [
        AgentTurnResponse(
            observation="First episode step 1",
            thought="Wait 10ms",
            done=False,
            actions=(WaitAction.parse_dict({
                "action": "wait",
                "duration": "10ms",
            }),),
        ),
        AgentTurnResponse(
            observation="First episode step 2",
            thought="Finish first episode",
            done=True,
            actions=(),
        ),
    ]
    second_client = MagicMock(spec=LlmConversationClient)
    second_client.send_turn.side_effect = [
        AgentTurnResponse(
            observation="Second episode step 1",
            thought="Wait 25ms and finish",
            done=True,
            actions=(WaitAction.parse_dict({
                "action": "wait",
                "duration": "25ms",
            }),),
        ),
    ]

    first_action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "First agent task",
        "max_steps": 5,
        "duration": "1m",
    })
    second_action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Second agent task",
        "max_steps": 5,
        "duration": "1m",
    })

    with (
        self.action_runner.info_stack_annotate("playback_0"),
        self.action_runner.info_stack_annotate("block_0"),
    ):
      with self.action_runner.info_stack_annotate("action_1"):
        first_driver = AgentDriver(
            self.action_runner,
            self.mock_run,
            first_action,
            client=first_client,
        )
        first_driver.execute()
      with self.action_runner.info_stack_annotate("action_2"):
        second_driver = AgentDriver(
            self.action_runner,
            self.mock_run,
            second_action,
            client=second_client,
        )
        second_driver.execute()

    expected_first_dir = (
        self.mock_run.out_dir / "agent_episodes" /
        "episode_000_playback_0_block_0_action_1")
    expected_second_dir = (
        self.mock_run.out_dir / "agent_episodes" /
        "episode_001_playback_0_block_0_action_2")
    self.assertEqual(first_driver.episode_dir, expected_first_dir)
    self.assertEqual(second_driver.episode_dir, expected_second_dir)

    self.assertTrue(
        (expected_first_dir / "screenshots" / "step_001.png").is_file())
    self.assertTrue(
        (expected_first_dir / "screenshots" / "step_002.png").is_file())
    self.assertTrue(
        (expected_second_dir / "screenshots" / "step_001.png").is_file())
    self.assertFalse(
        (expected_second_dir / "screenshots" / "step_002.png").exists())

    first_meta = json.loads(
        (expected_first_dir / "episode.json").read_text(encoding="utf-8"))
    second_meta = json.loads(
        (expected_second_dir / "episode.json").read_text(encoding="utf-8"))
    self.assertEqual(first_meta["action"]["prompt"], "First agent task")
    self.assertEqual(first_meta["info_stack"],
                     ["playback_0", "block_0", "action_1"])
    self.assertEqual(second_meta["action"]["prompt"], "Second agent task")
    self.assertEqual(second_meta["info_stack"],
                     ["playback_0", "block_0", "action_2"])

    first_transcript = (expected_first_dir / "transcript.jsonl").read_text(
        encoding="utf-8").strip().splitlines()
    second_transcript = (expected_second_dir / "transcript.jsonl").read_text(
        encoding="utf-8").strip().splitlines()
    self.assertEqual(len(first_transcript), 2)
    self.assertEqual(len(second_transcript), 1)
    self.assertEqual(
        json.loads(second_transcript[0])["episode_id"],
        "episode_001_playback_0_block_0_action_2",
    )
    self.assertEqual(json.loads(second_transcript[0])["step"], 1)

    first_replay = json.loads(
        (expected_first_dir /
         "replay_actions.hjson").read_text(encoding="utf-8"))
    second_replay = json.loads(
        (expected_second_dir /
         "replay_actions.hjson").read_text(encoding="utf-8"))
    self.assertEqual(first_replay["actions"][0]["duration"], 0.01)
    self.assertEqual(second_replay["actions"][0]["duration"], 0.025)

    self.assertIn("crossbench-agent_000_step_001_1_start",
                  self.browser.performance_marks)
    self.assertIn("crossbench-agent_001_step_001_1_start",
                  self.browser.performance_marks)

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

  def test_create_default_client(self) -> None:
    self.assertTrue(PROMPTS_DIR.is_dir())
    self.assertTrue(SYSTEM_INSTRUCTION_TEMPLATE_PATH.is_file())
    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Default client prompt",
        "model": "gemini-2.5-pro",
        "temperature": 1.4,
        "max_steps": 1,
        "duration": "1m",
        "max_history_screenshots": 4,
    })
    driver = AgentDriver(self.action_runner, self.mock_run, action)
    self.assertIsInstance(driver._client, LlmConversationClient)
    self.assertEqual(driver._client._model, "gemini-2.5-pro")
    self.assertEqual(driver._client._max_history_screenshots, 4)
    self.assertIsNone(driver._client._api_key)
    rendered_instruction = str(driver._client._config.system_instruction)
    self.assertIn("Default client prompt", rendered_instruction)
    self.assertNotIn("$prompt", rendered_instruction)
    self.assertIn('{"action": "click"', rendered_instruction)

    self.mock_run.story_secrets = Secrets.parse({"ai": "secret-ai-key"})
    driver_with_key = AgentDriver(self.action_runner, self.mock_run, action)
    self.assertEqual(driver_with_key._client._api_key, "secret-ai-key")

  def test_record_anomaly_clones_perfetto_snapshot_and_writes_anomalies(
      self) -> None:
    mock_client = MagicMock(spec=LlmConversationClient)
    mock_client.send_turn.side_effect = [
        AgentTurnResponse.parse({
            "observation": "Initial screen",
            "thought": "Normal step with whitespace anomaly field",
            "done": False,
            "anomaly": "   ",
            "actions": [],
        }),
        AgentTurnResponse.parse({
            "observation": "Second screen",
            "thought": "Report UI stall",
            "done": True,
            "anomaly": "Detected UI stall",
            "actions": [],
        }),
    ]
    mock_perfetto_ctx = MagicMock()

    def get_probe_ctx(probe_cls: type[Probe]) -> MagicMock | None:
      if probe_cls is PerfettoProbe:
        return mock_perfetto_ctx
      return None

    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Snapshot test",
        "max_steps": 3,
        "duration": "1m",
    })
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )
    with patch.object(
        self.mock_run, "get_probe_context", side_effect=get_probe_ctx):
      driver.execute()

    mock_perfetto_ctx.invoke.assert_called_once()
    anomalies_file = driver.episode_dir / "anomalies.json"
    self.assertTrue(anomalies_file.is_file())
    anomalies_data = json.loads(anomalies_file.read_text(encoding="utf-8"))
    self.assertEqual(len(anomalies_data), 1)
    self.assertEqual(anomalies_data[0]["episode_id"], "episode_000")
    self.assertEqual(anomalies_data[0]["step"], 2)
    self.assertEqual(anomalies_data[0]["anomaly"], "Detected UI stall")
    self.assertEqual(
        anomalies_data[0]["perfetto_snapshot_label"],
        "episode_000_step_002_anomaly",
    )

  def test_record_anomaly_clones_snapshot_on_every_anomaly_turn(self) -> None:
    mock_client = MagicMock(spec=LlmConversationClient)
    mock_client.send_turn.side_effect = [
        AgentTurnResponse.parse({
            "observation": "Step 1",
            "thought": "Report first stall",
            "done": False,
            "anomaly": "First stall",
            "actions": [],
        }),
        AgentTurnResponse.parse({
            "observation": "Step 2",
            "thought": "Report second stall immediately",
            "done": True,
            "anomaly": "Second stall",
            "actions": [],
        }),
    ]
    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "Consecutive snapshots test",
        "max_steps": 2,
        "duration": "1m",
        "settle_delay": "0s",
    })
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )
    mock_perfetto_ctx = MagicMock()
    with patch.object(
        self.mock_run, "get_probe_context", return_value=mock_perfetto_ctx):
      driver.execute()

    self.assertEqual(mock_perfetto_ctx.invoke.call_count, 2)
    anomalies_file = driver.episode_dir / "anomalies.json"
    anomalies_data = json.loads(anomalies_file.read_text(encoding="utf-8"))
    self.assertEqual(len(anomalies_data), 2)
    self.assertEqual(
        anomalies_data[0]["perfetto_snapshot_label"],
        "episode_000_step_001_anomaly",
    )
    self.assertEqual(
        anomalies_data[1]["perfetto_snapshot_label"],
        "episode_000_step_002_anomaly",
    )

  def test_record_anomaly_records_null_snapshot_when_perfetto_inactive(
      self) -> None:
    mock_client = MagicMock(spec=LlmConversationClient)
    mock_client.send_turn.side_effect = [
        AgentTurnResponse.parse({
            "observation": "Step 1",
            "thought": "Report stall without perfetto probe",
            "done": True,
            "anomaly": "Stall without perfetto",
            "actions": [],
        }),
    ]
    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": "No perfetto probe test",
        "max_steps": 1,
        "duration": "1m",
    })
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )
    driver.execute()

    anomalies_file = driver.episode_dir / "anomalies.json"
    self.assertTrue(anomalies_file.is_file())
    anomalies_data = json.loads(anomalies_file.read_text(encoding="utf-8"))
    self.assertEqual(len(anomalies_data), 1)
    self.assertEqual(anomalies_data[0]["anomaly"], "Stall without perfetto")
    self.assertIsNone(anomalies_data[0]["perfetto_snapshot_label"])

  def _setup_driver_with_screenshot(self, prompt: str) -> AgentDriver:
    mock_client = MagicMock(spec=LlmConversationClient)
    action = AgentAction.parse_dict({
        "action": "agent",
        "prompt": prompt,
        "max_steps": 1,
        "duration": "1m",
    })
    driver = AgentDriver(
        self.action_runner,
        self.mock_run,
        action,
        client=mock_client,
    )
    screenshots_dir = driver.episode_dir / "screenshots"
    self.fs.create_file(screenshots_dir / "step_001.png", contents="png")
    return driver

  def test_generate_timelapse_invokes_ffmpeg_when_screenshots_exist(
      self) -> None:
    driver = self._setup_driver_with_screenshot("Test timelapse")
    ffmpeg_path = pathlib.Path("/usr/bin/ffmpeg")
    with (
        patch.object(Binaries.FFMPEG, "search", return_value=ffmpeg_path),
        patch.object(self.platform, "sh") as mock_sh,
    ):
      driver._generate_timelapse()
      mock_sh.assert_called_once()
      call_args = mock_sh.call_args.args
      self.assertEqual(call_args[0], ffmpeg_path)
      self.assertIn("libwebp_anim", call_args)
      self.assertIn(driver.episode_dir / "timelapse.webp", call_args)

  def test_generate_timelapse_skips_when_ffmpeg_missing(self) -> None:
    driver = self._setup_driver_with_screenshot("Test timelapse without ffmpeg")
    with (
        patch.object(Binaries.FFMPEG, "search", return_value=None),
        patch.object(self.platform, "sh") as mock_sh,
    ):
      driver._generate_timelapse()
      mock_sh.assert_not_called()


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
