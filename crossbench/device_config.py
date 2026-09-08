# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
import enum
import logging
from collections.abc import Iterator, Mapping
from typing import TypeAlias, Union

from crossbench import hjson as cb_hjson
from crossbench import path as pth
from crossbench.config import ConfigEnum

DeviceConfigMap: TypeAlias = Mapping[str, Union[str, "DeviceConfigMap"]]
DeviceConfigFile: TypeAlias = pth.LocalPath
DeviceConfig: TypeAlias = DeviceConfigMap | DeviceConfigFile
_DeviceConfigKeyPath: TypeAlias = tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class _DeviceConfigDiscrepancy:
  """Represents a device configuration discrepancy."""
  key_path: _DeviceConfigKeyPath
  expected: str
  actual: DeviceConfigMap | str | None

  def __str__(self) -> str:
    path_str = ".".join(self.key_path)
    if self.actual is None:
      issue = "but value was absent"
    else:
      issue = f"got {self.actual!r}"
    return f"{path_str}: expected {self.expected!r}, {issue}."


@enum.unique
class RequiredDeviceConfigMode(ConfigEnum):
  THROW = ("throw", "Raise an error and abort on discrepancies.")
  WARN = ("warn", "Log discrepancies as critical warnings and continue.")


class DeviceConfigError(ValueError):
  """Raised when a device configuration discrepancy is encountered."""


def parse_device_config(config: DeviceConfig) -> DeviceConfigMap:
  """Loads a device config dictionary from a file or mapping."""
  data: DeviceConfigMap
  match config:
    case Mapping():
      data = config
    # AnyPath supports tests that patch LocalPath via pyfakefs.
    case pth.LocalPath() | pth.AnyPath():
      data = cb_hjson.loads_unique_keys(config.read_text(encoding="utf-8"))
    case _:
      raise DeviceConfigError(f"Invalid config type: {type(config)}")
  if not isinstance(data, Mapping):
    raise DeviceConfigError(f"Invalid config type: {type(data)}")
  return {key.lower(): val for key, val in data.items()}


def check_device_config(
    required: DeviceConfigMap,
    actual: DeviceConfigMap,
    mode: RequiredDeviceConfigMode,
) -> None:
  """Compares device configs and logs or raises on discrepancies.

  Args:
    required:
      The required configuration dictionary specifying expected values.
      Intermediate nodes must be nested mappings. Leaf nodes must be strings
      representing the expected value, or "null" if the setting is expected
      to be absent or null. Any non-string leaf value raises a ValueError.
    actual:
      The actual hierarchical device configuration dictionary.
    mode:
      The action to take on discrepancies (throw or warn).
  """
  if not (discrepancies := _compare_device_config(required, actual)):
    return

  items = "\n".join(f"  - {discrepancy}" for discrepancy in discrepancies)
  msg = f"Device config discrepancies:\n{items}"
  match mode:
    case RequiredDeviceConfigMode.WARN:
      logging.critical("%s", msg)
    case RequiredDeviceConfigMode.THROW | _:
      msg = f"{msg}\nUse --required-device-config-mode=warn to bypass."
      raise DeviceConfigError(msg)


def _compare_device_config(
    required: DeviceConfigMap,
    actual: DeviceConfigMap,
) -> list[_DeviceConfigDiscrepancy]:
  """Compares actual config against requirements and returns discrepancies."""
  discrepancies: list[_DeviceConfigDiscrepancy] = []
  for key_path, expected_value in _iter_device_config(required):
    actual_value = _get_device_config_value(actual, key_path)
    if discrepancy := _check_device_config_value(key_path, expected_value,
                                                 actual_value):
      discrepancies.append(discrepancy)
  return discrepancies


def _get_device_config_value(
    config: DeviceConfigMap,
    key_path: _DeviceConfigKeyPath,
) -> DeviceConfigMap | str | None:
  """Retrieves the value at key_path, or None if absent or unreachable."""
  current: DeviceConfigMap | str | None = config
  for key in key_path:
    if not isinstance(current, Mapping):
      return None
    current = current.get(key)
  return current


def _check_device_config_value(
    key_path: _DeviceConfigKeyPath,
    expected_value: str,
    actual_value: DeviceConfigMap | str | None,
) -> _DeviceConfigDiscrepancy | None:
  """Checks an expected setting and returns a discrepancy if mismatched."""
  if actual_value == expected_value:
    return None
  if actual_value is None and expected_value == "null":
    return None
  return _DeviceConfigDiscrepancy(key_path, expected_value, actual_value)


def _iter_device_config(
    config: DeviceConfigMap,
    prefix: _DeviceConfigKeyPath = (),
) -> Iterator[tuple[_DeviceConfigKeyPath, str]]:
  """Yields (key_path, expected_value) pairs from a hierarchical config.

  Leaf keys may contain delimiters (such as 'namespace/key' for Android
  device_config or 'ro.build.version' for getprop) and are treated as atomic
  leaf keys within their parent section.
  """
  for key, value in config.items():
    key_path = (*prefix, key)
    match value:
      case Mapping():
        yield from _iter_device_config(value, key_path)
      case str():
        yield key_path, value
      case _:
        formatted_key_path = ".".join(key_path)
        raise ValueError(f"Invalid config at {formatted_key_path}: {value!r}.")
