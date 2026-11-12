# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
import functools
from typing import TYPE_CHECKING, ClassVar, Self, override

from crossbench.action_runner.action.action import Action
from crossbench.action_runner.action.action_type import ActionType
from crossbench.parse import ObjectParser

if TYPE_CHECKING:
  from crossbench.action_runner.action_runner import ActionRunner
  from crossbench.config import ConfigParser
  from crossbench.types import JsonDict


@dataclasses.dataclass(frozen=True, eq=False)
class StartBrowserAction(Action):
  """Starts the session browser if it is not currently running."""

  TYPE: ClassVar[ActionType] = ActionType.START_BROWSER

  startup_urls: tuple[str, ...] = ()

  @classmethod
  @override
  @functools.lru_cache(maxsize=1)
  def config_parser(cls: type[Self]) -> ConfigParser[Self]:
    parser = super().config_parser()
    parser.add_default_argument(
      "startup_urls",
      type=ObjectParser.fuzzy_url_str,
      default=(),
      is_list=True,
      help="URLs to open immediately on browser launch "
      "(currently desktop Chromium only).",
    )
    return parser

  @override
  def validate(self) -> None:
    super().validate()
    for url in self.startup_urls:
      if not url:
        raise ValueError(f"{self}.startup_urls contains an empty URL.")

  @override
  def run_with(self, action_runner: ActionRunner) -> None:
    action_runner.start_browser(self)

  @override
  def to_json(self) -> JsonDict:
    details = super().to_json()
    details["startup_urls"] = list(self.startup_urls)
    return details
