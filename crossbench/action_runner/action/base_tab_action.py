# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import dataclasses
import functools
from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench.action_runner.action.action import Action, Self
from crossbench.parse import NumberParser, ObjectParser

if TYPE_CHECKING:
  import re

  from crossbench.config import ConfigParser
  from crossbench.types import JsonDict


@dataclasses.dataclass(frozen=True, eq=False)
class BaseTabAction(Action, metaclass=abc.ABCMeta):
  tab_index: int | None = None
  relative_tab_index: int | None = None
  title: re.Pattern | None = None
  url: re.Pattern | None = None

  @classmethod
  @override
  @functools.lru_cache(maxsize=1)
  def config_parser(cls: type[Self]) -> ConfigParser[Self]:
    parser = super().config_parser()
    parser.add_argument(
        "tab_index",
        type=NumberParser.any_int,
        help=(
            "The index of the tab. Tabs are indexed in creation "
            "order. Negative values are allowed, e.g. -1 is the most recently "
            "opened tab."))
    parser.add_argument(
        "relative_tab_index",
        type=NumberParser.any_int,
        help=("The index of the tab, relative to the current tab. -1 means the"
              "tab created just before this one."))
    parser.add_argument("title", type=ObjectParser.regexp)
    parser.add_argument("url", type=ObjectParser.regexp)
    return parser

  @override
  def validate(self) -> None:
    super().validate()
    if self.relative_tab_index is not None and self.tab_index is not None:
      raise ValueError("relative_tab_index and tab_index can not both be set")

  @override
  def to_json(self) -> JsonDict:
    details = super().to_json()
    if self.tab_index:
      details["tab_index"] = self.tab_index
    if self.title:
      details["title"] = str(self.title.pattern)
    if self.url:
      details["url"] = str(self.url.pattern)
    if self.relative_tab_index is not None:
      details["relative_tab_index"] = self.relative_tab_index
    return details
