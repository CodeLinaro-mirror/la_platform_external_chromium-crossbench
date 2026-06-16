# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Final, Self

from typing_extensions import override

from crossbench.config import ConfigObject, ConfigParser
from crossbench.parse import ObjectParser, PathParser
from crossbench.probes.trace_processor.constants import QUERIES_DIR
from crossbench.replacements import Replacements

if TYPE_CHECKING:
  from crossbench import path as pth
  from crossbench.plt import Platform


class TraceProcessorQueryConfig(ConfigObject):

  @classmethod
  @override
  def parse_dict(cls, config: dict[str, Any],
                 **kwargs) -> TraceProcessorQueryConfig:
    keys = {"device_override", "device_lookup", "sql_device_override"}
    if keys.intersection(config) and cls is TraceProcessorQueryConfig:
      return DeviceSpecificTraceProcessorQuery.parse_dict(config, **kwargs)
    return super().parse_dict(config, **kwargs)

  @classmethod
  @override
  def parse_str(cls, value: str) -> Self:
    name = ObjectParser.safe_filename(value)
    if value.endswith(".sql"):
      name = name[:-4]
    else:
      value = f"{value}.sql"
    sql_path = PathParser.existing_file_path(QUERIES_DIR / value, "sql query")
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

  def __init__(self,
               name: str,
               sql: str,
               replacements: Replacements | None = None) -> None:
    self._name: Final[str] = name
    self._sql: Final[str] = self._init_sql(sql, replacements)

  def _init_sql(self, sql: str, replacements: Replacements | None) -> str:
    if replacements:
      return replacements.apply(sql)
    return sql

  @property
  def name(self) -> str:
    return self._name

  @property
  def sql(self) -> str:
    return self._sql

  def resolve_for_platform(self,
                           platform: Platform) -> TraceProcessorQueryConfig:
    del platform
    return self


class DeviceSpecificTraceProcessorQuery(TraceProcessorQueryConfig):

  @classmethod
  @override
  def config_parser(cls) -> ConfigParser[Self]:
    parser = ConfigParser(cls)
    parser.add_argument("name", type=ObjectParser.safe_filename, required=True)
    parser.add_argument(
        "device_override",
        aliases=("device_lookup", "sql_device_override"),
        type=ObjectParser.dict,
        required=True)
    parser.add_argument("sql", type=str, required=False)
    parser.add_argument("replacements", aliases=("replace",), type=Replacements)
    return parser

  def __init__(self,
               name: str,
               device_override: dict[str, str],
               sql: str | None = None,
               replacements: Replacements | None = None) -> None:
    self._device_override: dict[re.Pattern, str] = {}
    for model, path in device_override.items():
      try:
        self._device_override[re.compile(model)] = path
      except re.error as e:
        raise ValueError(
            f"Invalid regular expression in device_override: {model}") from e
    self._fallback_sql = sql
    self._replacements = replacements
    super().__init__(name=name, sql="", replacements=None)

  @property
  @override
  def sql(self) -> str:
    raise RuntimeError(
        "DeviceSpecificTraceProcessorQuery must be resolved for a platform "
        "before accessing its SQL.")

  def resolve_for_platform(self,
                           platform: Platform) -> TraceProcessorQueryConfig:
    device_model = platform.model
    query_path = ""

    for model_re, path in self._device_override.items():
      if model_re.fullmatch(device_model):
        query_path = path
        break

    if not query_path:
      if self._fallback_sql:
        query_path = self._fallback_sql
      else:
        raise ValueError(f"Unsupported device model for query: {device_model}")

    value = f"{query_path}.sql"
    sql_path = PathParser.existing_file_path(QUERIES_DIR / value, "sql query")
    sql = sql_path.read_text(encoding="utf-8")
    return TraceProcessorQueryConfig(
        name=self.name, sql=sql, replacements=self._replacements)
