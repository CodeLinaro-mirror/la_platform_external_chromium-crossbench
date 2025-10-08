# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Self

from typing_extensions import override

from crossbench.config import ConfigObject, ConfigParser
from crossbench.parse import ObjectParser, PathParser
from crossbench.probes.trace_processor.constants import QUERIES_DIR
from crossbench.replacements import Replacements

if TYPE_CHECKING:
  from crossbench import path as pth


class TraceProcessorQueryConfig(ConfigObject):

  @classmethod
  @override
  def parse_str(cls, value: str) -> Self:
    name = ObjectParser.safe_filename(value)
    sql_path = PathParser.existing_file_path(QUERIES_DIR / f"{value}.sql",
                                             "sql query")
    sql = sql_path.read_text(encoding="utf-8")
    return cls(name=name, sql=sql)

  @classmethod
  @override
  def parse_any_path(cls, path: pth.LocalPath, **kwargs) -> Self:
    return cls.parse_str(str(path))

  @classmethod
  @override
  def resolve_path(cls, path: pth.LocalPath) -> pth.LocalPath:
    return path

  @classmethod
  @override
  def config_parser(cls) -> ConfigParser[Self]:
    parser = ConfigParser(cls)
    parser.add_argument("name", type=ObjectParser.safe_filename, required=True)
    parser.add_argument(
        "sql", type=ObjectParser.str_or_file_contents, required=True)
    parser.add_argument("replacements", aliases=("replace",), type=Replacements)
    return parser

  @property
  def name(self) -> str:
    return self._name

  @property
  def sql(self) -> str:
    return self._sql

  def __init__(self,
               name: str,
               sql: str,
               replacements: Optional[Replacements] = None) -> None:
    self._name = name
    self._sql = sql
    if replacements:
      self._sql = replacements.apply(self._sql)
