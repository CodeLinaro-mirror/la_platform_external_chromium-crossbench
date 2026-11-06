# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
import datetime as dt
import functools
import logging
import string
import time
from typing import TYPE_CHECKING, Final

from crossbench import path as pth
from crossbench.action_runner.action.action_type import ActionType
from crossbench.action_runner.action.click import ClickAction
from crossbench.action_runner.action.mouse_move import MouseMoveAction
from crossbench.action_runner.action.position import PositionConfig
from crossbench.action_runner.action.swipe import SwipeAction
from crossbench.action_runner.action.text_input import TextInputAction
from crossbench.action_runner.llm_client import LlmConversationClient
from crossbench.benchmarks.loading.point import Point
from crossbench.cli.ui import ui

if TYPE_CHECKING:
  from crossbench.action_runner.action.action import Action
  from crossbench.action_runner.action.agent import AgentAction
  from crossbench.action_runner.action_runner import ActionRunner
  from crossbench.action_runner.llm_client import AgentTurnResponse
  from crossbench.plt.base import Platform
  from crossbench.runner.run import Run

PROMPTS_DIR: Final[pth.LocalPath] = (
    pth.ROOT_DIR / "crossbench" / "action_runner" / "prompts")
SYSTEM_INSTRUCTION_TEMPLATE_PATH: Final[pth.LocalPath] = (
    PROMPTS_DIR / "agent_system_instruction.txt")


class AgentDriver:
  """Executes an AgentAction loop within a Crossbench Run."""

  MIN_TYPING_MS_PER_CHAR: Final[int] = 100

  def __init__(
      self,
      action_runner: ActionRunner,
      run: Run,
      action: AgentAction,
      client: LlmConversationClient | None = None,
  ) -> None:
    self._action_runner: Final[ActionRunner] = action_runner
    self._run: Final[Run] = run
    self._action: Final[AgentAction] = action
    self._session_dir: Final[pth.LocalPath] = run.out_dir / "agent_session"
    self._screenshots_dir: Final[pth.LocalPath] = (
        self._session_dir / "screenshots")
    self._display_resolution: Final[tuple[int, int]] = (
        self.browser_platform.display_resolution())
    self._client: LlmConversationClient = (
        client or self._create_default_client())

  @property
  def host_platform(self) -> Platform:
    return self._run.host_platform

  @property
  def browser_platform(self) -> Platform:
    return self._run.browser_platform

  def _resolve_api_key(self) -> str | None:
    if (run_secrets := self._run.secrets) and run_secrets.ai:
      return run_secrets.ai.api_key
    return None

  def _scale_coordinates(self, x: int, y: int) -> tuple[int, int]:
    width, height = self._display_resolution
    return (
        round(x * width / 1000.0),
        round(y * height / 1000.0),
    )

  def _ensure_realistic_typing_duration(
      self, action: TextInputAction) -> TextInputAction:
    if not action.text:
      return action
    min_duration = dt.timedelta(
        milliseconds=len(action.text) * self.MIN_TYPING_MS_PER_CHAR)
    if action.duration >= min_duration:
      return action
    return dataclasses.replace(action, duration=min_duration)

  def _scale_action_coordinates(self, action: Action) -> Action:
    # Multimodal LLMs natively emit screenshot coordinates in a normalized
    # 0..1000 space (independent of device/session display resolution).
    match action:
      case ClickAction():
        if coords := action.position.coordinates:
          scaled_x, scaled_y = self._scale_coordinates(coords.x, coords.y)
          return dataclasses.replace(
              action,
              position=PositionConfig.from_coordinates(scaled_x, scaled_y),
          )
        return action
      case SwipeAction():
        start_x, start_y = self._scale_coordinates(action.start_x,
                                                   action.start_y)
        end_x, end_y = self._scale_coordinates(action.end_x, action.end_y)
        return dataclasses.replace(
            action,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
        )
      case MouseMoveAction():
        scaled_waypoints = tuple(
            Point(*self._scale_coordinates(wp.x, wp.y))
            for wp in action.waypoints)
        return dataclasses.replace(action, waypoints=scaled_waypoints)
      case _:
        return action

  def prepare_sub_action(self, action: Action) -> Action:
    scaled = self._scale_action_coordinates(action)
    if isinstance(scaled, TextInputAction):
      return self._ensure_realistic_typing_duration(scaled)
    return scaled

  @functools.cached_property
  def _system_instruction_template(self) -> string.Template:
    return string.Template(
        SYSTEM_INSTRUCTION_TEMPLATE_PATH.read_text(encoding="utf-8"))

  def _create_default_client(self) -> LlmConversationClient:
    system_instruction = self._system_instruction_template.substitute(
        prompt=self._action.prompt)
    return LlmConversationClient(
        model=self._action.model,
        system_instruction=system_instruction,
        temperature=self._action.temperature,
        api_key=self._resolve_api_key(),
        max_history_screenshots=self._action.max_history_screenshots,
    )

  def _collect_environment_context(self) -> str:
    if tasks := self.browser_platform.get_active_tasks():
      task_lines = "\n".join(f"  - {task}" for task in tasks)
      return f"Active tasks ({len(tasks)} total):\n{task_lines}"
    return ""

  def _build_turn_feedback(self, feedback: str) -> str:
    if env_context := self._collect_environment_context():
      return f"{feedback}\n\n{env_context}"
    return feedback

  def _request_turn(self, step_idx: int, feedback: str) -> AgentTurnResponse:
    turn_feedback = self._build_turn_feedback(feedback)
    screenshot_bytes = self._capture_step_screenshot(step_idx)
    with (
        self._action_runner.actions(f"Agent step {step_idx}", measure=False),
        ui.timer("Waiting for agent"),
    ):
      logging.info("Agent step %d | waiting for agent response...", step_idx)
      turn = self._client.send_turn(turn_feedback, screenshot_bytes)
    logging.info("Agent step %d | thought: %s", step_idx, turn.thought)
    return turn

  def execute(self) -> None:
    self.host_platform.mkdir(self._screenshots_dir)
    start_time = time.monotonic()
    duration_s = self._action.duration.total_seconds()
    deadline = start_time + duration_s
    duration_total_s = int(duration_s)
    feedback = (
        "Agent session started. Observe the initial screen and emit your "
        "first action(s).")

    for step_idx in range(1, self._action.max_steps + 1):
      if time.monotonic() >= deadline:
        logging.info("AgentAction reached duration limit (%s) at step %d",
                     self._action.duration, step_idx)
        break

      turn = self._request_turn(step_idx, feedback)
      action_results = self._execute_turn_actions(step_idx, turn.actions)
      elapsed_total_s = int(time.monotonic() - start_time)
      feedback = (
          f"[Session elapsed: {elapsed_total_s}s / {duration_total_s}s | "
          f"Completed step {step_idx}]\n{action_results}")

      if turn.done:
        if self._action.stop_on_done:
          logging.info("AgentAction completed at step %d", step_idx)
          break
        feedback += (
            "\nEarly completion ('done': true) is disabled for this run. "
            "Do NOT idle or repeat simple scrolls in place — take your time "
            "exploring new pages, switching between open windows/tabs/apps, "
            "or starting a fresh round of tasks until the session timeout.")

      if self._action.settle_delay > dt.timedelta():
        self._run.runner.wait(self._action.settle_delay)

  def _capture_step_screenshot(self, step_idx: int) -> bytes:
    file_name = f"step_{step_idx:03d}.png"
    local_path = self._screenshots_dir / file_name
    if self.browser_platform.is_remote:
      remote_tmp = self._run.browser_tmp_dir / f"cb_agent_{file_name}"
      self.browser_platform.screenshot(remote_tmp)
      self.browser_platform.pull(remote_tmp, local_path)
      self.browser_platform.rm(remote_tmp, missing_ok=True)
    else:
      self.browser_platform.screenshot(local_path)
    return self.host_platform.cat_bytes(local_path)

  def _format_action_error(self, error: Exception) -> str:
    base_msg = type(error).__name__
    for line in str(error).splitlines():
      if stripped := line.strip():
        base_msg = f"{type(error).__name__}: {stripped}"
        break
    if not self._run.browser.is_running:
      return (f"{base_msg} (Browser is not running; use 'swipe' or "
              "coordinate/UI-selector actions on native OS screens, or "
              "'start_browser' first).")
    return base_msg

  def _execute_turn_actions(
      self,
      step_idx: int,
      actions: tuple[Action, ...],
  ) -> str:
    if not actions:
      return f"Step {step_idx}: Agent emitted no actions."
    return "\n".join(
        self._execute_sub_action(step_idx, sub_idx, sub_action)
        for sub_idx, sub_action in enumerate(actions, start=1))

  def _execute_sub_action(
      self,
      step_idx: int,
      sub_idx: int,
      raw_sub_action: Action,
  ) -> str:
    if raw_sub_action.TYPE == ActionType.AGENT:
      return f"Step {step_idx}.{sub_idx}: Nested agent action is not allowed."

    sub_action = self.prepare_sub_action(raw_sub_action)
    label = f"agent_step_{step_idx:03d}_{sub_idx}"
    self._run.performance_mark(f"{label}_start")
    t0 = time.monotonic()
    try:
      with self._action_runner.info_stack_annotate(label):
        sub_action.run_with(self._action_runner)
      elapsed_s = time.monotonic() - t0
      return (f"Step {step_idx}.{sub_idx} ({sub_action.TYPE}) "
              f"succeeded in {elapsed_s * 1000:.0f}ms.")
    except Exception as e:  # noqa: BLE001
      elapsed_s = time.monotonic() - t0
      err_detail = self._format_action_error(e)
      err_msg = (f"Step {step_idx}.{sub_idx} ({sub_action.TYPE}) "
                 f"failed after {elapsed_s * 1000:.0f}ms: {err_detail}")
      logging.warning(err_msg)
      logging.debug("Sub-action %s failed: %s", label, e, exc_info=True)
      return err_msg
    finally:
      self._run.performance_mark(f"{label}_end")
