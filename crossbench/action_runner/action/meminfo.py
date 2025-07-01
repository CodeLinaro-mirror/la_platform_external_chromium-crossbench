# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import enum
import functools
from typing import TYPE_CHECKING, Optional, Type

from typing_extensions import override

from crossbench.action_runner.action.action import Action, ACTION_TIMEOUT, ActionT
from crossbench.action_runner.action.action_type import ActionType
from crossbench.config import ConfigEnum
from crossbench.parse import ObjectParser

if TYPE_CHECKING:
  from crossbench.action_runner.base import ActionRunner
  from crossbench.config import ConfigParser
  from crossbench.runner.run import Run
  from crossbench.types import JsonDict


@enum.unique
class MeminfoTarget(ConfigEnum):
  BROWSER = ("browser", "The current target browser")
  PACKAGE = ("package",
             "A different package. Specify using the package_name field")


class MeminfoAction(Action):
  TYPE: ActionType = ActionType.MEMINFO

  @classmethod
  @override
  @functools.lru_cache(maxsize=1)
  def config_parser(cls: Type[ActionT]) -> ConfigParser[ActionT]:
    parser = super().config_parser()
    parser.add_argument(
        "target", type=MeminfoTarget, default=MeminfoTarget.BROWSER)
    parser.add_argument(
        "package", type=ObjectParser.non_empty_str, default=None)
    parser.add_argument("title", type=ObjectParser.non_empty_str, default=None)
    return parser

  def __init__(self,
               target: MeminfoTarget = MeminfoTarget.BROWSER,
               package: Optional[str] = None,
               title: Optional[str] = None,
               timeout: dt.timedelta = ACTION_TIMEOUT,
               index: int = 0) -> None:
    self._target = target
    self._package = package
    self._title = title
    super().__init__(timeout, index)

  @override
  def validate(self) -> None:
    super().validate()
    if self._target is MeminfoTarget.PACKAGE and not self.package:
      raise ValueError(
          f"{self}.target is 'package' but no package name was specified")

  @property
  def target(self) -> MeminfoTarget:
    return self._target

  @property
  def package(self) -> Optional[str]:
    return self._package

  @property
  def title(self) -> Optional[str]:
    return self._title

  @override
  def to_json(self) -> JsonDict:
    details = super().to_json()
    details["target"] = self.target
    if self.package:
      details["package"] = self.package
    if self.title:
      details["title"] = self.title
    return details

  @override
  def run_with(self, run: Run, action_runner: ActionRunner) -> None:
    action_runner.dump_meminfo(run, self)
