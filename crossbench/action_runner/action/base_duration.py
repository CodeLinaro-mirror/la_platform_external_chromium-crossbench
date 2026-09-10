# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
import datetime as dt
import functools
from typing import TYPE_CHECKING, ClassVar

from typing_extensions import override

from crossbench.action_runner.action.action import Action, Self
from crossbench.action_runner.action.action_type import ActionType
from crossbench.parse import DurationParser

if TYPE_CHECKING:
  from crossbench.config import ConfigParser
  from crossbench.types import JsonDict


@dataclasses.dataclass(frozen=True, eq=False)
class BaseDurationAction(Action):
  """Base class for actions with a duration (swipe, scroll, get, etc.)."""
  duration: dt.timedelta = dataclasses.field(
      default=dt.timedelta(), kw_only=True)

  @override
  def validate(self) -> None:
    super().validate()
    self.validate_duration()

  def validate_duration(self) -> None:
    if self.duration.total_seconds() <= 0:
      raise ValueError(
          f"{self}.duration should be positive, but got {self.duration}")

  @override
  def to_json(self) -> JsonDict:
    details = super().to_json()
    details["duration"] = self.duration.total_seconds()
    return details


@dataclasses.dataclass(frozen=True, eq=False)
class DurationAction(BaseDurationAction):
  """Base class for wait actions requiring an explicit duration argument."""
  TYPE: ClassVar[ActionType] = ActionType.WAIT

  @classmethod
  @override
  @functools.cache
  def config_parser(cls: type[Self]) -> ConfigParser[Self]:
    parser = super().config_parser()
    parser.add_argument(
        "duration", type=DurationParser.positive_duration, required=True)
    return parser
