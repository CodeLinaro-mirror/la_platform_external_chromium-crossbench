# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import abc
import collections.abc
import dataclasses
import re
from typing import TYPE_CHECKING, Iterator, Self, override

from immutabledict import immutabledict

from crossbench import exception
from crossbench.config import ConfigError, ConfigObject
from crossbench.helper.cwd import change_cwd
from crossbench.parse import ObjectParser, PathParser

if TYPE_CHECKING:
  from crossbench import path as pth


@dataclasses.dataclass(frozen=True)
class DeviceModelLookup[ValueT](
  ConfigObject,
  collections.abc.Mapping[re.Pattern[str], ValueT],
):
  """Abstract ConfigObject mapping device model regexes to domain values.

  Keys are full-match regular expressions tested against `Platform.model`
  (for example `ro.product.model` on Android). Concrete subclasses implement
  `_parse_entry_value` to parse each model's target configuration value.

  Example HJSON format (for an integer-valued lookup subclass):
    {
      "Pixel 9 Pro XL": 33,
      "SM-S928.*": 169
    }
  """

  entries: immutabledict[re.Pattern[str], ValueT] = dataclasses.field(
    default_factory=immutabledict
  )

  @override
  def __getitem__(self, key: re.Pattern[str]) -> ValueT:
    return self.entries[key]

  @override
  def __iter__(self) -> Iterator[re.Pattern[str]]:
    return iter(self.entries)

  @override
  def __len__(self) -> int:
    return len(self.entries)

  @classmethod
  @abc.abstractmethod
  def _parse_entry_value(cls, model_pattern: str, raw_value: object) -> ValueT:
    """Parses and validates a single model pattern's raw value."""
    raise NotImplementedError

  @classmethod
  @override
  def parse_str(cls, value: str) -> Self:
    raise ConfigError(f"Cannot parse {cls.__name__} from string: {value!r}")

  @classmethod
  @override
  def parse_path_like(
    cls, original_value: str, path: pth.LocalPath, **kwargs: object
  ) -> Self:
    del original_value
    return cls.parse_any_path(path, **kwargs)

  @classmethod
  @override
  def parse_other(cls, value: object, **kwargs: object) -> Self:
    if isinstance(value, collections.abc.Mapping) and not isinstance(
      value, ConfigObject
    ):
      return cls.parse_dict(dict(value), **kwargs)
    cls.expect_no_extra_kwargs(kwargs)
    return super().parse_other(value)

  @classmethod
  @override
  def parse_dict(cls, config: dict[str, object], **kwargs: object) -> Self:
    cls.expect_no_extra_kwargs(kwargs)
    entries: dict[re.Pattern[str], ValueT] = {}
    for raw_key, raw_value in config.items():
      key = ObjectParser.non_empty_str(raw_key, "device model regex key")
      pattern = ObjectParser.regexp(key, f"mapping key '{key}'")
      entries[pattern] = cls._parse_entry_value(key, raw_value)
    return cls(immutabledict(entries))

  @classmethod
  @override
  def parse_hjson_path(cls, path: pth.LocalPathLike, **kwargs: object) -> Self:
    with exception.annotate_argparsing(f"Parsing {cls.__name__} file: {path}"):
      file_path = PathParser.existing_file_path(path)
      raw_mapping = ObjectParser.dict(
        ObjectParser.hjson_file(file_path), name=str(file_path)
      )
      with change_cwd(file_path.parent):
        result = cls.parse_dict(raw_mapping, **kwargs)
    return result

  def merge(self, other: Self) -> Self:
    """Combines lookups, raising ConfigError on same-key value conflicts."""
    merged = dict(self.entries)
    for pattern, value in other.entries.items():
      if pattern in merged and merged[pattern] != value:
        raise ConfigError(
          f"Conflicting mapping for pattern '{pattern.pattern}': "
          f"{merged[pattern]!r} and {value!r}"
        )
      merged[pattern] = value
    return type(self)(immutabledict(merged))

  def resolve(self, device_model: str) -> ValueT | None:
    """Returns the matching value, raising ValueError on conflicts."""
    matched_value: ValueT | None = None
    has_match = False
    for model_re, value in self.entries.items():
      if not model_re.fullmatch(device_model):
        continue
      if has_match and matched_value != value:
        raise ValueError(
          "Multiple conflicting mappings match device model "
          f"'{device_model}': {matched_value!r} and {value!r}"
        )
      matched_value = value
      has_match = True
    return matched_value
