# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import logging
import time
from typing import TYPE_CHECKING, Final

from crossbench.action_runner.action.action_type import ActionType
from crossbench.cli.ui import ui

if TYPE_CHECKING:
  from crossbench import path as pth
  from crossbench.action_runner.action.action import Action
  from crossbench.action_runner.action.agent import AgentAction
  from crossbench.action_runner.action_runner import ActionRunner
  from crossbench.action_runner.llm_client import AgentTurnResponse, \
      LlmConversationClient
  from crossbench.plt.base import Platform
  from crossbench.runner.run import Run


class AgentDriver:
  """Executes an AgentAction loop within a Crossbench Run."""

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
    self._client: LlmConversationClient = (
        client or self._create_default_client())

  @property
  def host_platform(self) -> Platform:
    return self._run.host_platform

  @property
  def browser_platform(self) -> Platform:
    return self._run.browser_platform

  def _create_default_client(self) -> LlmConversationClient:
    raise NotImplementedError(
        "Default LlmConversationClient is not implemented yet")

  def _request_turn(self, step_idx: int, feedback: str) -> AgentTurnResponse:
    screenshot_bytes = self._capture_step_screenshot(step_idx)
    with (
        self._action_runner.actions(f"Agent step {step_idx}", measure=False),
        ui.timer("Waiting for agent"),
    ):
      logging.info("Agent step %d | waiting for agent response...", step_idx)
      turn = self._client.send_turn(feedback, screenshot_bytes)
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
      sub_action: Action,
  ) -> str:
    if sub_action.TYPE == ActionType.AGENT:
      return f"Step {step_idx}.{sub_idx}: Nested agent action is not allowed."

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
