# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, ClassVar

from typing_extensions import override

from crossbench.action_runner.action.action import ACTION_TIMEOUT, Action, Self
from crossbench.action_runner.action.action_type import ActionType
from crossbench.parse import ObjectParser

if TYPE_CHECKING:
  import datetime as dt
  import re

  from crossbench.action_runner.base import ActionRunner
  from crossbench.config import ConfigParser
  from crossbench.types import JsonDict


class WaitForUrlMatchesAction(Action):
  TYPE: ClassVar[ActionType] = ActionType.WAIT_FOR_URL_MATCHES

  @classmethod
  @override
  @functools.lru_cache(maxsize=1)
  def config_parser(cls: type[Self]) -> ConfigParser[Self]:
    parser = super().config_parser()
    parser.add_argument("url_pattern", type=ObjectParser.regexp, required=True)
    return parser

  def __init__(self,
               url_pattern: re.Pattern[str],
               timeout: dt.timedelta = ACTION_TIMEOUT,
               index: int = 0) -> None:
    self._url_pattern = url_pattern
    super().__init__(timeout, index)

  @property
  def url_pattern(self) -> re.Pattern[str]:
    return self._url_pattern

  @override
  def run_with(self, action_runner: ActionRunner) -> None:
    action_runner.wait_for_url_matches(self)

  @override
  def to_json(self) -> JsonDict:
    details = super().to_json()
    details["url_pattern"] = self._url_pattern.pattern
    return details
