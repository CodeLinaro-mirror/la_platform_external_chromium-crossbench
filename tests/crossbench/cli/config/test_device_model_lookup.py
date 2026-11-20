# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import dataclasses
import inspect
import re
from typing import override

from immutabledict import immutabledict

from crossbench import path as pth
from crossbench.cli.config.device_model_lookup import DeviceModelLookup
from crossbench.cli.subcommand.describe import get_all_config_classes
from crossbench.config import ConfigError
from crossbench.parse import NumberParser, ObjectParser, PathParser
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


@dataclasses.dataclass(frozen=True)
class _IntModelLookup(DeviceModelLookup[int]):
  """Test lookup mapping device model regexes to non-negative integers."""

  @classmethod
  @override
  def _parse_entry_value(cls, model_pattern: str, raw_value: object) -> int:
    return NumberParser.positive_zero_int(
      raw_value, f"test value for '{model_pattern}'"
    )


@dataclasses.dataclass(frozen=True)
class _StrModelLookup(DeviceModelLookup[str]):
  """Sibling lookup subclass for testing foreign ConfigObject rejection."""

  @classmethod
  @override
  def _parse_entry_value(cls, model_pattern: str, raw_value: object) -> str:
    return ObjectParser.non_empty_str(raw_value, model_pattern)


@dataclasses.dataclass(frozen=True)
class _PathModelLookup(DeviceModelLookup[pth.LocalPath]):
  """Lookup subclass resolving relative entry paths against HJSON parent dir."""

  @classmethod
  @override
  def _parse_entry_value(
    cls, model_pattern: str, raw_value: object
  ) -> pth.LocalPath:
    return PathParser.existing_file_path(raw_value, model_pattern).resolve()


class DeviceModelLookupTestCase(CrossbenchFakeFsTestCase):
  def test_abstract_base_is_excluded_from_describe_configs(self) -> None:
    config_classes = get_all_config_classes()

    self.assertTrue(inspect.isabstract(DeviceModelLookup))
    self.assertNotIn(DeviceModelLookup, config_classes)

  def test_parse_dict_resolves_full_matches_only(self) -> None:
    raw = {"Pixel 9 Pro XL": 33, r"Pixel 10\b.*": 28}

    lookup = _IntModelLookup.parse(raw)

    self.assertEqual(lookup.resolve("Pixel 9 Pro XL"), 33)
    self.assertEqual(lookup.resolve("Pixel 10 Pro"), 28)
    self.assertIsNone(lookup.resolve("Pixel 9 Pro"))
    self.assertIsNone(lookup.resolve("Pixel 100"))

  def test_parse_immutabledict_and_mapping_interface(self) -> None:
    raw = immutabledict({"Model A": 12})

    lookup = _IntModelLookup.parse(raw)

    self.assertEqual(len(lookup), 1)
    self.assertEqual(dict(lookup), {re.compile("Model A"): 12})
    self.assertEqual(lookup[re.compile("Model A")], 12)

  def test_parse_foreign_lookup_subclass_raises(self) -> None:
    other = _StrModelLookup()

    with self.assertRaisesRegex(
      argparse.ArgumentTypeError, "Invalid config input type"
    ):
      _IntModelLookup.parse(other)

  def test_parse_inline_hjson_string(self) -> None:
    inline = '{"Pixel 9 Pro XL": 33, "Pixel 10 Pro XL": 28}'

    lookup = _IntModelLookup.parse(inline)

    self.assertEqual(lookup.resolve("Pixel 9 Pro XL"), 33)
    self.assertEqual(lookup.resolve("Pixel 10 Pro XL"), 28)

  def test_parse_plain_string_raises(self) -> None:
    with self.assertRaisesRegex(
      argparse.ArgumentTypeError, "Cannot parse _IntModelLookup from string"
    ):
      _IntModelLookup.parse("plain-string")

  def test_parse_empty_key_raises(self) -> None:
    with self.assertRaisesRegex(
      argparse.ArgumentTypeError, "device model regex key"
    ):
      _IntModelLookup.parse({"": 10})

  def test_parse_invalid_regex_raises(self) -> None:
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "Invalid regexp"):
      _IntModelLookup.parse({"[unclosed": 10})

  def test_parse_invalid_entry_value_raises(self) -> None:
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "test value"):
      _IntModelLookup.parse({"Model A": -1})

  def test_parse_hjson_file(self) -> None:
    mapping_path = pth.LocalPath("/configs/mapping.hjson")
    self.fs.create_file(mapping_path, contents='{"Model A": 42}')

    lookup = _IntModelLookup.parse(mapping_path)

    self.assertEqual(lookup.resolve("Model A"), 42)

  def test_parse_empty_hjson_file(self) -> None:
    empty_path = pth.LocalPath("/configs/empty.hjson")
    self.fs.create_file(empty_path, contents="{}")

    empty_lookup = _IntModelLookup.parse(empty_path)

    self.assertEqual(len(empty_lookup), 0)

  def test_parse_missing_file_raises(self) -> None:
    missing = pth.LocalPath("/configs/missing.hjson")

    with self.assertRaisesRegex(argparse.ArgumentTypeError, "does not exist"):
      _IntModelLookup.parse(missing)

  def test_parse_missing_path_string_raises(self) -> None:
    with self.assertRaisesRegex(
      argparse.ArgumentTypeError, "Path does not exist"
    ):
      _IntModelLookup.parse("./missing.hjson")

  def test_parse_hjson_file_annotates_errors_and_changes_cwd(self) -> None:
    target_file = pth.LocalPath("/configs/sub/target.txt")
    mapping_path = pth.LocalPath("/configs/mapping.hjson")
    invalid_path = pth.LocalPath("/configs/invalid.hjson")
    self.fs.create_file(target_file, contents="ok")
    self.fs.create_file(mapping_path, contents='{"Model A": "sub/target.txt"}')
    self.fs.create_file(invalid_path, contents='{"Model A": -1}')

    lookup = _PathModelLookup.parse(mapping_path)

    self.assertEqual(lookup.resolve("Model A"), target_file.resolve())
    with self.assertRaisesRegex(
      argparse.ArgumentTypeError,
      "Parsing _IntModelLookup file: /configs/invalid.hjson",
    ):
      _IntModelLookup.parse(invalid_path)

  def test_merge_combines_disjoint_and_agreeing_entries(self) -> None:
    base = _IntModelLookup.parse({"Model A": 10, "Shared": 20})
    extra = _IntModelLookup.parse({"Model B": 30, "Shared": 20})

    merged = base.merge(extra)

    self.assertEqual(merged.resolve("Model A"), 10)
    self.assertEqual(merged.resolve("Shared"), 20)
    self.assertEqual(merged.resolve("Model B"), 30)

  def test_merge_conflicting_same_pattern_raises(self) -> None:
    base = _IntModelLookup.parse({"Shared": 20})
    extra = _IntModelLookup.parse({"Shared": 25})

    with self.assertRaisesRegex(
      ConfigError, "Conflicting mapping for pattern 'Shared'"
    ):
      base.merge(extra)

  def test_resolve_overlapping_agreeing_patterns_succeeds(self) -> None:
    lookup = _IntModelLookup.parse({r"Pixel.*": 28, r"Pixel 10.*": 28})

    resolved = lookup.resolve("Pixel 10 Pro")

    self.assertEqual(resolved, 28)

  def test_resolve_overlapping_conflicting_patterns_raises(self) -> None:
    lookup = _IntModelLookup.parse({r"Pixel.*": 33, r"Pixel 10.*": 28})

    with self.assertRaisesRegex(
      ValueError, "Multiple conflicting mappings match device model"
    ):
      lookup.resolve("Pixel 10 Pro")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
