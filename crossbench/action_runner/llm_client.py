# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from crossbench.action_runner.action.action import Action


@dataclasses.dataclass(frozen=True)
class AgentTurnResponse:
  """Structured single-turn response emitted by an LLM agent."""
  observation: str = ""
  thought: str = ""
  done: bool = False
  actions: tuple[Action, ...] = ()


class LlmConversationClient:
  """Stateful multi-turn LLM chat client."""

  def send_turn(
      self,
      feedback_text: str,
      screenshot_bytes: bytes | None = None,
  ) -> AgentTurnResponse:
    del feedback_text, screenshot_bytes
    raise NotImplementedError("LlmConversationClient is not implemented yet")
