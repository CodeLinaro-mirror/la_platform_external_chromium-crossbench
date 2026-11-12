# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
import datetime as dt
import functools
from typing import TYPE_CHECKING, ClassVar, Final, Self, override

from crossbench.action_runner.action.action_type import ActionType
from crossbench.action_runner.action.base_duration import BaseDurationAction
from crossbench.parse import DurationParser, NumberParser, ObjectParser

if TYPE_CHECKING:
  from crossbench.action_runner.action_runner import ActionRunner
  from crossbench.config import ConfigParser
  from crossbench.types import JsonDict

DEFAULT_AGENT_MODEL: Final[str] = "gemini-3.8-flash"
DEFAULT_AGENT_TEMPERATURE: Final[float] = 1.0
DEFAULT_AGENT_MAX_STEPS: Final[int] = 25
DEFAULT_AGENT_DURATION: Final[dt.timedelta] = dt.timedelta(minutes=5)
DEFAULT_SETTLE_DELAY: Final[dt.timedelta] = dt.timedelta(seconds=5)
DEFAULT_MAX_HISTORY_SCREENSHOTS: Final[int] = 3


@dataclasses.dataclass(frozen=True, eq=False)
class AgentAction(BaseDurationAction):
  """Executes a multi-turn LLM-guided interaction loop within a story.

  Captures screenshots on each step, sends them with execution feedback to the
  configured Gemini model, and runs the returned Crossbench sub-actions until
  completion, `max_steps`, or `duration` is reached.
  """

  TYPE: ClassVar[ActionType] = ActionType.AGENT

  prompt: str = ""
  model: str = DEFAULT_AGENT_MODEL
  temperature: float = DEFAULT_AGENT_TEMPERATURE
  max_steps: int = DEFAULT_AGENT_MAX_STEPS
  settle_delay: dt.timedelta = DEFAULT_SETTLE_DELAY
  stop_on_done: bool = True
  max_history_screenshots: int = DEFAULT_MAX_HISTORY_SCREENSHOTS
  # Overrides BaseDurationAction.duration:
  duration: dt.timedelta = dataclasses.field(
    default=DEFAULT_AGENT_DURATION, kw_only=True
  )

  @classmethod
  @override
  def parse_str(cls, value: str) -> Self:
    return cls.config_parser().parse_str(value)

  @classmethod
  @override
  @functools.cache
  def config_parser(cls: type[Self]) -> ConfigParser[Self]:
    parser = super().config_parser()
    parser.add_default_argument(
      "prompt",
      aliases=("instructions", "goal"),
      type=ObjectParser.non_empty_str,
      required=True,
      help="Natural-language task instructions for the agent.",
    )
    parser.add_argument(
      "model",
      type=ObjectParser.non_empty_str,
      default=DEFAULT_AGENT_MODEL,
      help="Gemini model identifier used to drive agent turns.",
    )
    parser.add_argument(
      "temperature",
      aliases=("temp",),
      type=NumberParser.float_range(0.0, 2.0, name="temperature"),
      default=DEFAULT_AGENT_TEMPERATURE,
      help="Sampling temperature in [0.0, 2.0] for model responses.",
    )
    parser.add_argument(
      "max_steps",
      aliases=("steps",),
      type=NumberParser.positive_int,
      default=DEFAULT_AGENT_MAX_STEPS,
      help="Maximum number of agent turns to execute.",
    )
    parser.add_argument(
      "duration",
      type=DurationParser.positive_duration,
      default=DEFAULT_AGENT_DURATION,
      help="Maximum wall-clock duration for the agent session.",
    )
    parser.add_argument(
      "settle_delay",
      type=DurationParser.positive_or_zero_duration,
      default=DEFAULT_SETTLE_DELAY,
      help="Wait duration inserted after each non-terminal turn.",
    )
    parser.add_argument(
      "stop_on_done",
      type=ObjectParser.bool,
      default=True,
      help="Whether to exit the loop early when the agent sets done=true.",
    )
    parser.add_argument(
      "max_history_screenshots",
      aliases=("max_screenshots",),
      type=NumberParser.positive_zero_int,
      default=DEFAULT_MAX_HISTORY_SCREENSHOTS,
      help="Number of recent turn screenshots retained in chat history.",
    )
    return parser

  @override
  def run_with(self, action_runner: ActionRunner) -> None:
    action_runner.agent(self)

  @override
  def validate(self) -> None:
    super().validate()
    if not self.prompt:
      raise ValueError(f"{self}.prompt is missing")
    if not self.model:
      raise ValueError(f"{self}.model is missing")
    NumberParser.float_range(0.0, 2.0, name="temperature")(self.temperature)
    NumberParser.positive_int(self.max_steps, f"{self}.max_steps")
    DurationParser.positive_or_zero_duration(
      self.settle_delay, f"{self}.settle_delay"
    )
    NumberParser.positive_zero_int(
      self.max_history_screenshots, f"{self}.max_history_screenshots"
    )

  @override
  def to_json(self) -> JsonDict:
    details = super().to_json()
    details["prompt"] = self.prompt
    details["model"] = self.model
    details["temperature"] = self.temperature
    details["max_steps"] = self.max_steps
    details["settle_delay"] = self.settle_delay.total_seconds()
    details["stop_on_done"] = self.stop_on_done
    details["max_history_screenshots"] = self.max_history_screenshots
    return details
