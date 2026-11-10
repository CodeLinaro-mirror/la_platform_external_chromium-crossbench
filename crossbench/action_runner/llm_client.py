# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
import functools
from typing import TYPE_CHECKING, Final, Self, override

from google import genai
from google.genai import types

from crossbench.action_runner.action.action import Action
from crossbench.action_runner.action.all import ACTIONS_TUPLE
from crossbench.config import ConfigError, ConfigObject, ConfigParser
from crossbench.parse import NumberParser, ObjectParser

if TYPE_CHECKING:
  from google.genai import chats

# Force registration of all Action subclasses before parsing Action items.
assert ACTIONS_TUPLE, "import failed"


@dataclasses.dataclass(frozen=True)
class AgentTurnResponse(ConfigObject):
  """Structured single-turn JSON response emitted by an LLM agent.

  Contains the agent's current screen observation, reasoning, completion status,
  optional anomaly description, and the sequence of Crossbench actions to
  execute next.
  """
  observation: str = ""
  thought: str = ""
  done: bool = False
  anomaly: str = ""
  actions: tuple[Action, ...] = ()

  @classmethod
  @override
  def parse_str(cls, value: str) -> Self:
    raise ConfigError(
        f"Expected JSON object for {cls.__name__}, got: {value!r}")

  @classmethod
  @override
  @functools.cache
  def config_parser(cls) -> ConfigParser[Self]:
    parser = ConfigParser(cls)
    parser.add_argument(
        "observation",
        type=ObjectParser.any_str,
        default="",
        help="Summary of what is visible on screen and prior action outcome.")
    parser.add_argument(
        "thought",
        type=ObjectParser.any_str,
        default="",
        help="Reasoning for the next step based on the task instructions.")
    parser.add_argument(
        "done",
        type=ObjectParser.bool,
        default=False,
        help="Whether the requested task instructions are complete.")
    parser.add_argument(
        "anomaly",
        type=ObjectParser.any_str,
        default="",
        help=("Non-empty description when an anomaly is observed on this turn "
              "(records an entry in anomalies.json and clones a Perfetto "
              "snapshot)."))
    parser.add_argument(
        "actions",
        type=Action,
        default=(),
        is_list=True,
        help="Ordered Crossbench actions to execute in this turn.")
    return parser


class LlmConversationClient:
  """Stateful multi-turn LLM chat client."""

  def __init__(
      self,
      model: str,
      system_instruction: str,
      temperature: float,
      api_key: str | None = None,
      genai_client: genai.Client | None = None,
      max_history_screenshots: int = 3,
  ) -> None:
    self._model: Final[str] = ObjectParser.non_empty_str(model, "model")
    system_instruction = ObjectParser.non_empty_str(system_instruction,
                                                    "system_instruction")
    temperature = NumberParser.float_range(
        0.0, 2.0, name="temperature")(
            temperature)
    self._max_history_screenshots: Final[int] = NumberParser.positive_zero_int(
        max_history_screenshots, "max_history_screenshots")
    if api_key is not None:
      api_key = ObjectParser.non_empty_str(api_key, "api_key")
    self._api_key: Final[str | None] = api_key
    self._genai_client: genai.Client | None = genai_client
    self._http_options: Final[types.HttpOptions] = types.HttpOptions(
        retry_options=types.HttpRetryOptions())
    self._config: Final[types.GenerateContentConfig] = (
        types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json",
            http_options=self._http_options,
        ))
    self._chat: chats.Chat | None = None

  @property
  def genai_client(self) -> genai.Client:
    if self._genai_client is None:
      self._genai_client = genai.Client(
          api_key=self._api_key,
          http_options=self._http_options,
      )
    return self._genai_client

  @property
  def chat(self) -> chats.Chat:
    if self._chat is None:
      self._chat = self.genai_client.chats.create(
          model=self._model,
          config=self._config,
      )
    return self._chat

  def _prune_prompt_history_data(self) -> None:
    history: list[types.Content] = self.chat.get_history(curated=True)
    kept_screenshots = 0
    for content in reversed(history):
      if not (parts := content.parts):
        continue
      if not any(part.inline_data is not None for part in parts):
        continue
      if kept_screenshots < self._max_history_screenshots:
        kept_screenshots += 1
      else:
        content.parts = [part for part in parts if part.inline_data is None]

  def send_turn(
      self,
      feedback_text: str,
      screenshot_bytes: bytes | None = None,
  ) -> AgentTurnResponse:
    self._prune_prompt_history_data()
    user_parts: list[types.PartUnionDict] = [
        types.Part.from_text(text=feedback_text),
    ]
    if screenshot_bytes:
      user_parts.append(
          types.Part.from_bytes(
              data=screenshot_bytes,
              mime_type="image/png",
          ))
    response = self.chat.send_message(user_parts)
    if not (model_text := response.text):
      raise RuntimeError(f"Model returned empty response text: {response}")
    return AgentTurnResponse.parse(model_text)
