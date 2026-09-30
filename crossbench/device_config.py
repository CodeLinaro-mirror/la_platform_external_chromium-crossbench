# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import dataclasses
import enum
import logging
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any, ClassVar, TypeAlias

from typing_extensions import override

from crossbench import hjson as cb_hjson
from crossbench import path as pth
from crossbench.config import ConfigEnum

DeviceConfigValue: TypeAlias = (
    str | Sequence["DeviceConfigValue"] | Mapping[str, "DeviceConfigValue"])
DeviceConfigMap: TypeAlias = Mapping[str, DeviceConfigValue]
DeviceConfigFile: TypeAlias = pth.LocalPath
DeviceConfig: TypeAlias = DeviceConfigMap | DeviceConfigFile
DeviceConfigKeyPath: TypeAlias = tuple[str, ...]

# Operator keys, such as "$regex", start with this prefix. Device
# configuration keys never do, so the two cannot collide.
_OPERATOR_PREFIX = "$"


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
  a section that imposes no requirements. Leaf nodes specify expectations and
  can be one of:
  - Exact string: "expected_val" (or "null" for an absent setting).
  - Disjunction list: [item1, item2, ...] matching if any item matches.
  - Mapping:
      - {"$regex": "pattern"}: matches the actual value in full.
    Keys starting with '$' are operators: a mapping containing any of them
    is a requirement rather than a section.

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
  assert not _has_reserved_keys(actual), "Unexpected $ in device config."

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


def _has_reserved_keys(config: DeviceConfigMap) -> bool:
  """Returns whether any config key is reserved for operator syntax.

  Device configurations are expected to have none. A requirement naming
  such a key would be parsed as an operator instead, leaving the setting
  unreachable.
  """
  return any(
      key.startswith(_OPERATOR_PREFIX) or
      (isinstance(value, Mapping) and _has_reserved_keys(value))
      for key, value in config.items())


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
      # A mapping holding an operator key is a requirement. Any other
      # mapping is a subsection; an empty one imposes no requirements.
      has_operator = any(k.startswith(_OPERATOR_PREFIX) for k in value)
      if not has_operator:
        yield from _iter_device_config(value, key_path)
        continue
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
      case Mapping():
        return _MappingPredicate.parse_mapping(value)
      # Strings and bytes are sequences, but are not requirement lists.
      case Sequence() if not isinstance(value, (str, bytes)):
        return _AnyOfPredicate.parse_sequence(value)
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


class _MappingPredicate(_Predicate):
  """Predicate parsable from a mapping of operator keys it declares."""

  # Populated by subclasses.
  registry: ClassVar[dict[frozenset[str], type[_MappingPredicate]]] = {}

  def __init_subclass__(cls, keys: Iterable[str], **kwargs: Any) -> None:
    super().__init_subclass__(**kwargs)
    config_keys = frozenset(keys)
    assert all(key.startswith(_OPERATOR_PREFIX) for key in config_keys)
    # No operator key may be registered by more than one subclass. This
    # guarantees parse_mapping() matches at most one subclass, regardless of
    # the registry's iteration order.
    assert not any(config_keys & k for k in _MappingPredicate.registry)
    _MappingPredicate.registry[config_keys] = cls

  @staticmethod
  def parse_mapping(mapping: DeviceConfigMap) -> _Predicate:
    """Parses a mapping leaf into a predicate."""
    if not mapping:
      raise ValueError("Invalid empty configuration mapping.")
    keys = list(mapping.keys())
    present = frozenset(keys)
    for config_keys, predicate in _MappingPredicate.registry.items():
      if present <= config_keys:
        return predicate.from_mapping(mapping)
    raise ValueError(f"Invalid config: unknown or conflicting keys {keys!r}.")

  @classmethod
  @abc.abstractmethod
  def from_mapping(cls, mapping: DeviceConfigMap) -> _Predicate:
    """Parses a mapping whose keys this predicate owns."""


@dataclasses.dataclass(frozen=True)
class _RegexPredicate(_MappingPredicate, keys={"$regex"}):
  """Matches if the actual value matches a regular expression pattern."""
  pattern: re.Pattern[str]

  @classmethod
  @override
  def from_mapping(cls, mapping: DeviceConfigMap) -> _RegexPredicate:
    raw_regex = mapping.get("$regex")
    if not isinstance(raw_regex, str):
      raise ValueError(f"Invalid $regex: expected str, got {raw_regex!r}.")
    try:
      pattern = re.compile(raw_regex)
    except re.error as e:
      raise ValueError(f"Invalid $regex: {raw_regex!r} ({e}).") from e
    return cls(pattern)

  @override
  def matches(self, actual: DeviceConfigValue | None) -> bool:
    return isinstance(actual, str) and bool(self.pattern.fullmatch(actual))

  @override
  def expected_str(self) -> str:
    return f"a full match for pattern '{self.pattern.pattern}'"


@dataclasses.dataclass(frozen=True)
class _AnyOfPredicate(_Predicate):
  """Matches if any of the sub-predicates match."""
  predicates: tuple[_Predicate, ...]

  @classmethod
  def parse_sequence(cls,
                     sequence: Sequence[DeviceConfigValue]) -> _AnyOfPredicate:
    if not sequence:
      raise ValueError(f"Invalid empty requirement list: {sequence!r}.")
    return cls(tuple(_Predicate.parse(item) for item in sequence))

  @override
  def matches(self, actual: DeviceConfigValue | None) -> bool:
    return any(p.matches(actual) for p in self.predicates)

  @override
  def expected_str(self) -> str:
    options = ", ".join(p.expected_str() for p in self.predicates)
    return f"any of ({options})"
