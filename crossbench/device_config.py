# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import dataclasses
import enum
import logging
from collections.abc import Iterator, Mapping
from typing import TypeAlias

from typing_extensions import override

from crossbench import hjson as cb_hjson
from crossbench import path as pth
from crossbench.config import ConfigEnum

DeviceConfigValue: TypeAlias = str | Mapping[str, "DeviceConfigValue"]
DeviceConfigMap: TypeAlias = Mapping[str, DeviceConfigValue]
DeviceConfigFile: TypeAlias = pth.LocalPath
DeviceConfig: TypeAlias = DeviceConfigMap | DeviceConfigFile
DeviceConfigKeyPath: TypeAlias = tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class DeviceConfigDiscrepancy:
  """Represents a device configuration discrepancy."""
  key_path: DeviceConfigKeyPath
  expectation: str
  actual: DeviceConfigValue | None

  def __str__(self) -> str:
    path_str = ".".join(self.key_path)
    if self.actual is None:
      issue = "value was absent"
    else:
      issue = f"got {self.actual!r}"
    return f"{path_str}: {issue}, expected {self.expectation}."


@dataclasses.dataclass(frozen=True)
class DeviceConfigRequirement:
  """A predicate bound to a specific key in the configuration tree."""
  key_path: DeviceConfigKeyPath
  predicate: _Predicate

  # TODO: support a 'target' value to write to the device when the
  # requirement is not met, for a future RequiredDeviceConfigMode.SET.

  @classmethod
  def parse(cls, key_path: DeviceConfigKeyPath,
            value: DeviceConfigValue) -> DeviceConfigRequirement:
    """Parses a leaf value, annotating parse errors with its key path."""
    try:
      predicate = _Predicate.parse(value)
    except ValueError as e:
      raise DeviceConfigError(f"{'.'.join(key_path)}: {e}") from e
    return cls(key_path, predicate)

  def check(
      self,
      actual: DeviceConfigValue | None,
  ) -> DeviceConfigDiscrepancy | None:
    """Returns a discrepancy if the actual value fails the predicate."""
    if self.predicate.matches(actual):
      return None
    return DeviceConfigDiscrepancy(self.key_path, self.predicate.expected_str(),
                                   actual)


# The immutable, parsed requirements of a single platform.
DeviceConfigRequirements: TypeAlias = tuple[DeviceConfigRequirement, ...]


@enum.unique
class RequiredDeviceConfigMode(ConfigEnum):
  THROW = ("throw", "Raise an error and abort on discrepancies.")
  WARN = ("warn", "Log discrepancies as critical warnings and continue.")


class DeviceConfigError(ValueError):
  """Raised on a malformed device configuration, or on a discrepancy."""


def parse_required_device_config(
    config: DeviceConfig) -> Mapping[str, DeviceConfigRequirements]:
  """Loads and validates device config requirements from a file or mapping.

  Top-level keys name platforms and are lower-cased; their values are the
  requirement sections. Nested keys are passed through verbatim, as device
  settings are case-sensitive.

  Raises:
    DeviceConfigError: If the config or any of its requirements is malformed.
  """
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
  required: dict[str, DeviceConfigRequirements] = {}
  for platform, section in data.items():
    if not isinstance(section, Mapping):
      msg = f"{platform}: Invalid platform section: {section!r}."
      raise DeviceConfigError(msg)
    try:
      required[platform.lower()] = _parse_platform_requirements(section)
    except DeviceConfigError as e:
      raise DeviceConfigError(f"{platform}: {e}") from e
  return required


def _parse_platform_requirements(
    config: DeviceConfigMap) -> DeviceConfigRequirements:
  """Parses one platform's requirement section.

  Intermediate nodes must be nested mappings, with an empty mapping denoting
  a section that imposes no requirements. Leaf nodes must be strings giving
  the exact expected value, or "null" if the setting is expected to be
  absent.

  Raises:
    DeviceConfigError: If any requirement is malformed.
  """
  return tuple(_iter_device_config(config))


def check_device_config(
    required: DeviceConfigRequirements,
    actual: DeviceConfigMap,
    mode: RequiredDeviceConfigMode,
) -> None:
  """Compares a device config against requirements, logging or raising.

  Args:
    required:
      The parsed requirements for the platform under test.
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
    case RequiredDeviceConfigMode.THROW:
      msg = f"{msg}\nUse --required-device-config-mode=warn to bypass."
      raise DeviceConfigError(msg)
    case _:
      msg = f"Unhandled device config mode: {mode!r}.\n{msg}"
      raise DeviceConfigError(msg)


def _compare_device_config(
    required: DeviceConfigRequirements,
    actual: DeviceConfigMap,
) -> list[DeviceConfigDiscrepancy]:
  """Compares actual config against requirements and returns discrepancies."""
  discrepancies: list[DeviceConfigDiscrepancy] = []
  for requirement in required:
    actual_value = _get_device_config_value(actual, requirement.key_path)
    if discrepancy := requirement.check(actual_value):
      discrepancies.append(discrepancy)
  return discrepancies


def _get_device_config_value(
    config: DeviceConfigMap,
    key_path: DeviceConfigKeyPath,
) -> DeviceConfigValue | None:
  """Retrieves the value at key_path, or None if absent or unreachable."""
  current: DeviceConfigValue | None = config
  for key in key_path:
    if not isinstance(current, Mapping):
      return None
    current = current.get(key)
  return current


def _iter_device_config(
    config: DeviceConfigMap,
    prefix: DeviceConfigKeyPath = (),
) -> Iterator[DeviceConfigRequirement]:
  """Yields the leaf requirements of a hierarchical config.

  Leaf keys may contain delimiters (such as 'namespace/key' for Android
  device_config or 'ro.build.version' for getprop) and are treated as atomic
  leaf keys within their parent section.
  """
  for key, value in config.items():
    key_path = (*prefix, key)
    if isinstance(value, Mapping):
      yield from _iter_device_config(value, key_path)
    else:
      yield DeviceConfigRequirement.parse(key_path, value)


class _Predicate(abc.ABC):
  """Abstract predicate for validating a device configuration value."""

  @staticmethod
  def parse(value: DeviceConfigValue) -> _Predicate:
    """Parses a leaf configuration into a predicate.

    Raises:
      ValueError: If the value is not a valid leaf configuration.
    """
    match value:
      case str():
        return _ValuePredicate.parse_str(value)
      case _:
        raise ValueError(f"Invalid config: {value!r}.")

  @abc.abstractmethod
  def matches(self, actual: DeviceConfigValue | None) -> bool:
    """Returns True if the actual value matches the predicate condition."""

  @abc.abstractmethod
  def expected_str(self) -> str:
    """Returns a string describing the expected requirement."""


@dataclasses.dataclass(frozen=True)
class _ValuePredicate(_Predicate):
  """Matches an exact string value, or absent/None if expected is 'null'."""
  expected: str

  @classmethod
  def parse_str(cls, value: str) -> _ValuePredicate:
    return cls(value)

  @override
  def matches(self, actual: DeviceConfigValue | None) -> bool:
    if actual is None:
      return self.expected == "null"
    return actual == self.expected

  @override
  def expected_str(self) -> str:
    return repr(self.expected)
