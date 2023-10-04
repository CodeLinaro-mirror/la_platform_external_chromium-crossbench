# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
""" A collection of helpers that rely on non-crossbench code."""

from __future__ import annotations

import enum
import pathlib
import sys
import textwrap
from typing import List, Tuple

import tabulate

if sys.version_info >= (3, 11):
  from enum import StrEnum
else:

  class StrEnum(str, enum.Enum):

    def __str__(self) -> str:
      return str(self.value)


if sys.version_info >= (3, 9):

  def is_relative_to(path_a: pathlib.Path, path_b: pathlib.Path) -> bool:
    return path_a.is_relative_to(path_b)
else:

  def is_relative_to(path_a: pathlib.Path, path_b: pathlib.Path) -> bool:
    try:
      path_a.relative_to(path_b)
      return True
    except ValueError:
      return False


class EnumWithHelp(enum.Enum):

  def __new__(cls, value, help_str: str = ""):
    del help_str
    obj = object.__new__(cls)
    obj._value_ = value
    return obj

  def __init__(self, value, help_str: str = "") -> None:
    del value
    assert help_str, "Missing help_str"
    self._help = help_str

  @property
  def help(self) -> str:
    return self._help

  @classmethod
  def help_text_items(cls) -> List[Tuple[str, str]]:
    return [(repr(instance.value), instance.help) for instance in cls]

  @classmethod
  def help_text(cls, indent: int = 0) -> str:
    text: str = tabulate.tabulate(cls.help_text_items(), tablefmt="plain")
    if indent:
      return textwrap.indent(text, " " * indent)
    return text


class StrEnumWithHelp(EnumWithHelp):

  def __str__(self) -> str:
    return str(self.value)
