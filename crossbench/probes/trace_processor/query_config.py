# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import dataclasses
import os
from typing import TYPE_CHECKING, Mapping, Self, override

from crossbench import path as pth
from crossbench.cli.config.device_model_lookup import DeviceModelLookup
from crossbench.config import ConfigObject, ConfigParser
from crossbench.parse import ObjectParser, PathParser
from crossbench.probes.trace_processor.constants import QUERIES_DIR
from crossbench.replacements import Replacements

if TYPE_CHECKING:
  from crossbench.plt import Platform


@dataclasses.dataclass(frozen=True)
class TraceProcessorQueryConfig(ConfigObject):
  name: str
  _sql: str

  @classmethod
  @override
  def create(
    cls,
    name: str,
    sql: str,
    replacements: Replacements | None = None,
  ) -> Self:
    if replacements:
      sql = replacements.apply(sql)
    return cls(name=name, _sql=sql)

  @classmethod
  @override
  def parse_dict(
    cls, config: dict[str, object], **kwargs
  ) -> TraceProcessorQueryConfig:
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
    return cls.create(name=name, sql=sql)

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
      "sql", type=ObjectParser.str_or_file_contents, required=True
    )
    parser.add_argument("replacements", aliases=("replace",), type=Replacements)
    return parser

  @property
  def sql(self) -> str:
    return self._sql

  def resolve_for_platform(
    self, platform: Platform
  ) -> TraceProcessorQueryConfig | None:
    del platform
    return self


def _parse_query_path(raw_value: object, name: str = "sql") -> pth.LocalPath:
  if isinstance(raw_value, os.PathLike):
    raw_value = os.fspath(raw_value)
  raw_str = ObjectParser.non_empty_str(raw_value, name)
  query_path = pth.LocalPath(raw_str).expanduser()
  if not query_path.name:
    raise argparse.ArgumentTypeError(
      f"Expected non-empty {name} filename: {raw_str!r}"
    )
  if query_path.suffix != ".sql":
    query_path = query_path.with_name(f"{query_path.name}.sql")
  return PathParser.existing_file_path(QUERIES_DIR / query_path, name).resolve()


@dataclasses.dataclass(frozen=True)
class DeviceSqlQueryLookup(DeviceModelLookup[pth.LocalPath]):
  """Maps device model regexes to TraceProcessor SQL query paths.

  Example:
    {
      "Pixel 9.*": "web_power/power_rails_tensor_g4",
      "Pixel 10.*": "web_power/power_rails_tensor_g5"
    }
  """

  @classmethod
  @override
  def _parse_entry_value(
    cls, model_pattern: str, raw_value: object
  ) -> pth.LocalPath:
    return _parse_query_path(
      raw_value, f"device_override query for '{model_pattern}'"
    )


@dataclasses.dataclass(frozen=True)
class DeviceSpecificTraceProcessorQuery(TraceProcessorQueryConfig):
  device_override: DeviceSqlQueryLookup = dataclasses.field(
    default_factory=DeviceSqlQueryLookup
  )
  fallback_sql: pth.LocalPath | None = None
  replacements: Replacements | None = None

  @classmethod
  @override
  def create(
    cls,
    name: str,
    sql: pth.LocalPathLike | None = None,
    replacements: Replacements | None = None,
    device_override: (
      DeviceSqlQueryLookup | Mapping[str, pth.LocalPathLike] | None
    ) = None,
  ) -> Self:
    fallback_sql: pth.LocalPath | None = None
    if sql is not None:
      fallback_sql = _parse_query_path(sql, "fallback sql")
    parsed_override = DeviceSqlQueryLookup()
    if device_override is not None:
      parsed_override = DeviceSqlQueryLookup.parse(device_override)
    return cls(
      name=name,
      _sql="",
      device_override=parsed_override,
      fallback_sql=fallback_sql,
      replacements=replacements,
    )

  @classmethod
  @override
  def config_parser(cls) -> ConfigParser[Self]:
    parser = ConfigParser(cls)
    parser.add_argument("name", type=ObjectParser.safe_filename, required=True)
    parser.add_argument(
      "device_override",
      aliases=("device_lookup", "sql_device_override"),
      type=DeviceSqlQueryLookup,
      required=True,
    )
    parser.add_argument("sql", type=str, required=False)
    parser.add_argument("replacements", aliases=("replace",), type=Replacements)
    return parser

  @property
  @override
  def sql(self) -> str:
    raise RuntimeError(
      "DeviceSpecificTraceProcessorQuery must be resolved for a platform "
      "before accessing its SQL."
    )

  def resolve_for_platform(
    self, platform: Platform
  ) -> TraceProcessorQueryConfig | None:
    return self.resolve_for_device_model(platform.model)

  def _resolve_query_path(self, device_model: str) -> pth.LocalPath | None:
    return self.device_override.resolve(device_model) or self.fallback_sql

  def resolve_for_device_model(
    self, device_model: str
  ) -> TraceProcessorQueryConfig | None:
    if query_path := self._resolve_query_path(device_model):
      return TraceProcessorQueryConfig.create(
        name=self.name,
        sql=query_path.read_text(encoding="utf-8"),
        replacements=self.replacements,
      )
    return None
