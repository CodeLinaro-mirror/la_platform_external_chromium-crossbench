# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import contextlib
import copy
import json
import logging
import subprocess
import unittest
from typing import Any, Iterator
from unittest import mock

from crossbench import path as pth
from crossbench.benchmarks.base import Benchmark
from crossbench.config import ConfigError
from crossbench.device_config import DeviceConfigError, DeviceConfigKeyPath, \
    DeviceConfigMap, DeviceConfigSetter, DeviceConfigValueError, \
    RequiredDeviceConfig, RequiredDeviceConfigMode, check_device_config
from crossbench.exception import ArgumentTypeMultiException
from crossbench.plt.android_adb import AndroidAdbPlatform
from crossbench.plt.base import Platform, SubprocessError
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.mock_helper import LinuxMockPlatform, MockStory


def check_config(required: DeviceConfigMap, actual: DeviceConfigMap,
                 mode: RequiredDeviceConfigMode) -> None:
  """Parses one platform's requirements and checks them, as the runner does."""
  parsed = parse_inline({"platform": required})
  check_device_config(parsed.platforms["platform"], actual, mode)


def parse_inline(config: dict[str, Any]) -> RequiredDeviceConfig:
  """Parses an inline config, raising errors unwrapped.

  Unlike RequiredDeviceConfig.parse(), parse_dict() does not wrap errors in
  an ArgumentTypeError, so tests can assert on the exact error type.
  """
  return RequiredDeviceConfig.parse_dict(config)


class DeviceConfigParserTestCase(CrossbenchFakeFsTestCase):
  """Tests for parsing device configuration files and mappings."""

  def assert_parse_raises(
      self,
      config: Any,
      expected_message: str,
      cause: type[Exception] = DeviceConfigError,
  ) -> None:
    """Asserts that parsing raises an argument error, wrapping cause."""
    with self.assertRaises(ArgumentTypeMultiException) as cm:
      RequiredDeviceConfig.parse(config)
    self.assertIn(expected_message, str(cm.exception))
    self.assertTrue(cm.exception.matching(cause))

  def test_parse_mapping(self):
    """Verify that a mapping input is parsed into platform requirements."""
    config = {"android": {"key": "val"}}
    self.assertEqual(
        list(RequiredDeviceConfig.parse(config).platforms), ["android"])

  def test_parse_lowercases_top_level_keys(self):
    """Verify that top-level platform keys are normalized to lower case."""
    config = {"Android": {"key": "val"}, "MacOS": {"other": "val2"}}
    required = RequiredDeviceConfig.parse(config).platforms
    self.assertEqual(sorted(required), ["android", "macos"])

  def test_parse_empty_platform_section(self):
    """Verify an empty platform section imposes no requirements."""
    # An empty section is the only way to state "nothing is required here".
    required = RequiredDeviceConfig.parse({"android": {}})
    self.assertEqual(required.platforms, {"android": ()})

  def test_parse_empty_subsection_adds_no_requirements(self):
    """Verify an empty subsection contributes nothing beside a real one."""
    config = {"android": {"settings": {}, "key": "val"}}
    required = RequiredDeviceConfig.parse(config).platforms
    self.assertEqual(len(required["android"]), 1)

  def test_parse_non_mapping_platform_section_raises(self):
    """Verify an error when a platform section is not a mapping."""
    self.assert_parse_raises({"android": "val"}, "android: Invalid section")

  def test_parse_valid_json_file(self):
    """Verify that JSON files are parsed."""
    path = pth.LocalPath("/config.json")
    self.fs.create_file(path, contents=json.dumps({"android": {"key": "val"}}))
    self.assertEqual(
        list(RequiredDeviceConfig.parse(path).platforms), ["android"])

  def test_parse_valid_hjson_file(self):
    """Verify that Hjson files are parsed."""
    path = pth.LocalPath("/config.hjson")
    hjson_content = """
    # Device configuration comment.
    {
      android: {
        // Line comment.
        key: "val",
      }
    }
    """
    self.fs.create_file(path, contents=hjson_content)
    self.assertEqual(
        list(RequiredDeviceConfig.parse(path).platforms), ["android"])

  def test_parse_missing_file_raises(self):
    """Verify an error when the config file does not exist."""
    self.assert_parse_raises(
        pth.LocalPath("/nonexistent.json"),
        "Path does not exist",
        cause=argparse.ArgumentTypeError)

  def test_parse_invalid_json_raises(self):
    """Verify an error when parsing invalid Hjson/JSON content."""
    path = pth.LocalPath("/invalid.hjson")
    self.fs.create_file(path, contents="{not-json")
    self.assert_parse_raises(
        path, "Invalid hjson file", cause=argparse.ArgumentTypeError)

  def test_parse_duplicate_keys_raises(self):
    """Verify an error when parsing config with duplicate keys."""
    path = pth.LocalPath("/duplicate.hjson")
    self.fs.create_file(path, contents='{"key": 1, "key": 2}')
    self.assert_parse_raises(
        path, "Duplicate key in hjson: key", cause=argparse.ArgumentTypeError)

  def test_parse_non_mapping_file_raises(self):
    """Verify an error when config file content is not a mapping."""
    path = pth.LocalPath("/list.json")
    self.fs.create_file(path, contents='["not", "a", "mapping"]')
    self.assert_parse_raises(
        path, "Invalid config input type list", cause=ConfigError)

    scalar_path = pth.LocalPath("/scalar.json")
    self.fs.create_file(scalar_path, contents='"just_a_string"')
    self.assert_parse_raises(scalar_path,
                             "Invalid device config: 'just_a_string'.")

  def test_parse_invalid_type_raises(self):
    """Verify an error when input is neither mapping nor path."""
    self.assert_parse_raises(
        12345, "Invalid config input type int", cause=ConfigError)

  def test_parse_string_path(self):
    """Verify that a string path is parsed like a path."""
    config = {"android": {"key": "val"}}
    self.fs.create_file("/config.json", contents=json.dumps(config))
    required = RequiredDeviceConfig.parse("/config.json")
    self.assertEqual(list(required.platforms), ["android"])

  def test_parse_inline_hjson(self):
    """Verify that an inline hjson string is parsed like a mapping."""
    required = RequiredDeviceConfig.parse('{android: {key: "val"}}')
    self.assertEqual(list(required.platforms), ["android"])

  def test_parsed_platforms_are_immutable(self):
    """Verify that parsed platforms cannot be modified."""
    required = RequiredDeviceConfig.parse({"android": {"key": "val"}})
    with self.assertRaises(TypeError):
      required.platforms["macos"] = ()  # type: ignore[index]

  def test_parse_validates_requirements(self):
    """Verify an error on a malformed requirement."""
    config = {"android": {"settings": {"key": 5}}}
    self.assert_parse_raises(config, "settings.key: Invalid config: 5.")

  def test_parse_validates_requirements_from_file(self):
    """Verify an error on a malformed requirement in a file."""
    path = pth.LocalPath("/invalid_requirement.json")
    self.fs.create_file(path, contents=json.dumps({"android": {"key": 5}}))
    self.assert_parse_raises(path, "key: Invalid config: 5.")

  def test_parse_validates_other_platform_sections(self):
    """Verify requirements are validated for every platform, not just one."""
    config = {"android": {"key": "val"}, "macos": {"key": 5}}
    self.assert_parse_raises(config, "key: Invalid config: 5.")

  def test_parse_errors_and_discrepancies_are_distinct(self):
    """Verify only malformed requirements raise a ConfigError."""
    with self.assertRaises(ConfigError) as parse_cm:
      parse_inline({"platform": {"key": 5}})
    self.assertNotIsInstance(parse_cm.exception, DeviceConfigValueError)

    with self.assertRaises(DeviceConfigValueError) as check_cm:
      check_config({"key": "val"}, {}, RequiredDeviceConfigMode.THROW)
    self.assertNotIsInstance(check_cm.exception, ConfigError)


class DeviceConfigTestCase(unittest.TestCase):
  """Tests for the requirement grammar, comparison and platform querying."""

  _REQUIRED_IMMERSIVE_CONFIRMED: DeviceConfigMap = {
      "settings": {
          "secure": {
              "immersive_mode_confirmations": "confirmed",
          },
      },
  }

  def assert_check_raises(self, required: Any, actual: Any,
                          expected_message: str) -> None:
    """Assert that check_device_config raises the expected error."""
    with self.assertRaises(DeviceConfigValueError) as cm:
      check_config(required, actual, RequiredDeviceConfigMode.THROW)
    self.assertIn(expected_message, str(cm.exception))

  def assert_parse_raises(self, required: Any, expected_message: str) -> None:
    """Assert that parsing the requirements raises the expected error."""
    with self.assertRaises(DeviceConfigError) as cm:
      parse_inline({"platform": required})
    self.assertIn(expected_message, str(cm.exception))

  def _create_mock_android_platform(self) -> tuple[mock.Mock, mock.Mock]:
    """Create a mock AndroidAdbPlatform wired with real config methods."""
    mock_adb = mock.Mock()
    platform = mock.create_autospec(AndroidAdbPlatform, instance=True)
    platform.adb = mock_adb
    platform.device_config.side_effect = (
        lambda: AndroidAdbPlatform.device_config(platform))
    platform.system_details.side_effect = (
        lambda: AndroidAdbPlatform.system_details(platform))
    return platform, mock_adb

  def test_exact_match(self):
    """Verify that matching required and actual configs pass validation."""
    config = {
        **self._REQUIRED_IMMERSIVE_CONFIRMED,
        "device_config": {
            "accessibility/font_scale": "1.0",
        },
    }
    check_config(config, config, RequiredDeviceConfigMode.THROW)

  def test_major_mismatch_default(self):
    """Verify value mismatches raise DeviceConfigValueError in THROW mode."""
    actual = {
        "settings": {
            "secure": {
                "immersive_mode_confirmations": "null",
            },
        },
    }
    self.assert_check_raises(
        self._REQUIRED_IMMERSIVE_CONFIRMED,
        actual,
        "settings.secure.immersive_mode_confirmations: "
        "got 'null', expected 'confirmed'.",
    )

  def test_absent_setting_normalized_to_null(self):
    """Verify that absent settings match when requirement expects 'null'."""
    # Key completely absent in actual settings.
    actual: dict[str, Any] = {
        "settings": {
            "secure": {},
        },
    }
    # Requirement expects "null" (or None).
    required = {
        "settings": {
            "secure": {
                "non_existent_key": "null",
            },
        },
    }
    check_config(required, actual, RequiredDeviceConfigMode.THROW)

  def test_absent_setting_fails_when_value_required(self):
    """Verify that absent settings raise when a concrete value is required."""
    self.assert_check_raises(
        self._REQUIRED_IMMERSIVE_CONFIRMED,
        {"settings": {
            "secure": {},
        }},
        "settings.secure.immersive_mode_confirmations: "
        "value was absent, expected 'confirmed'.",
    )

  def test_mapping_in_actual_when_null_required(self):
    """Verify error when actual has sub-mapping but expects 'null'."""
    # Actual has a sub-mapping, but requirement expects "null".
    actual = {
        "settings": {
            "secure": {
                "some_setting": "1",
            },
        },
    }
    required = {
        "settings": {
            "secure": "null",
        },
    }
    self.assert_check_raises(
        required,
        actual,
        "settings.secure: got {'some_setting': '1'}, expected 'null'.",
    )

  def test_missing_section_when_child_requires_null(self):
    """Verify that a missing parent section passes if child expects 'null'."""
    # Section "secure" is completely absent from actual settings.
    actual: dict[str, Any] = {
        "settings": {},
    }
    required = {
        "settings": {
            "secure": {
                "non_existent_key": "null",
            },
        },
    }
    check_config(required, actual, RequiredDeviceConfigMode.THROW)

  def test_missing_section_when_child_requires_value(self):
    """Verify error when parent section is absent but child needs a value."""
    # Section "secure" is completely absent from actual settings.
    self.assert_check_raises(
        self._REQUIRED_IMMERSIVE_CONFIRMED,
        {"settings": {}},
        "settings.secure.immersive_mode_confirmations: "
        "value was absent, expected 'confirmed'.",
    )

  def test_top_level_section_missing(self):
    """Verify error when the actual configuration dictionary is empty."""
    self.assert_check_raises(
        self._REQUIRED_IMMERSIVE_CONFIRMED,
        {},
        "settings.secure.immersive_mode_confirmations: "
        "value was absent, expected 'confirmed'.",
    )

  def test_primitive_in_actual_when_section_required(self):
    """Verify error when actual has a primitive where a mapping is needed."""
    actual = {
        "settings": {
            "secure": "not_a_mapping",
        },
    }
    self.assert_check_raises(
        self._REQUIRED_IMMERSIVE_CONFIRMED,
        actual,
        "settings.secure.immersive_mode_confirmations: "
        "value was absent, expected 'confirmed'.",
    )

  def test_non_string_primitive_in_actual_when_string_required(self):
    """Verify error when actual value has a primitive type mismatch."""
    actual = {
        "settings": {
            "secure": {
                "flag": 123,
            },
        },
    }
    required = {
        "settings": {
            "secure": {
                "flag": "123",
            },
        },
    }
    self.assert_check_raises(
        required,
        actual,
        "settings.secure.flag: got 123, expected '123'.",
    )

  def test_empty_required_config(self):
    """Verify that an empty required config matches any actual config."""
    check_config(
        {},
        self._REQUIRED_IMMERSIVE_CONFIRMED,
        RequiredDeviceConfigMode.THROW,
    )

  def test_extra_keys_in_actual_ignored(self):
    """Verify that extra keys in actual config are ignored during check."""
    actual = {
        "settings": {
            "secure": {
                "immersive_mode_confirmations": "confirmed",
                "extra_key": "extra_val",
            },
            "extra_section": {
                "flag": "1",
            },
        },
    }
    check_config(
        self._REQUIRED_IMMERSIVE_CONFIRMED,
        actual,
        RequiredDeviceConfigMode.THROW,
    )

  def test_check_device_config_warn_mode(self):
    """Verify that discrepancies log critical messages in WARN mode."""
    actual = {
        "settings": {
            "secure": {
                "immersive_mode_confirmations": "null",
            },
        },
    }
    with self.assertLogs(level=logging.CRITICAL) as cm:
      check_config(
          self._REQUIRED_IMMERSIVE_CONFIRMED,
          actual,
          mode=RequiredDeviceConfigMode.WARN)
    self.assertTrue(
        any("settings.secure.immersive_mode_confirmations: "
            "got 'null', expected 'confirmed'." in log for log in cm.output))

  def test_check_device_config_warn_mode_multiple_discrepancies(self):
    """Verify that all discrepancies are logged in WARN mode."""
    actual = {
        "settings": {
            "secure": {
                "immersive_mode_confirmations": "null",
            },
        },
    }
    required = {
        "settings": {
            "secure": {
                "immersive_mode_confirmations": "confirmed",
                "another_key": "val",
            },
        },
    }
    with self.assertLogs(level=logging.CRITICAL) as cm:
      check_config(required, actual, mode=RequiredDeviceConfigMode.WARN)
    logs = "\n".join(cm.output)
    self.assertIn(
        "settings.secure.immersive_mode_confirmations: "
        "got 'null', expected 'confirmed'.", logs)
    self.assertIn(
        "settings.secure.another_key: "
        "value was absent, expected 'val'.", logs)

  def test_check_device_config_warn_mode_no_discrepancies(self):
    """Verify that no warnings are logged when configs match in WARN mode."""
    with self.assertNoLogs(level=logging.WARNING):
      check_config(
          self._REQUIRED_IMMERSIVE_CONFIRMED,
          self._REQUIRED_IMMERSIVE_CONFIRMED,
          mode=RequiredDeviceConfigMode.WARN)

  def test_multiple_discrepancies(self):
    """Verify that multiple discrepancies across sections are all reported."""
    actual: DeviceConfigMap = {
        "settings": {
            "secure": {
                "immersive_mode_confirmations": "null",
            },
        },
        "device_config": {
            "accessibility/font_scale": "2.0",
        },
    }
    required: DeviceConfigMap = {
        "settings": {
            "secure": {
                "immersive_mode_confirmations": "confirmed",
            },
        },
        "device_config": {
            "accessibility/font_scale": "1.0",
            "runtime_native/flag_one": "42",
        },
    }
    with self.assertRaises(DeviceConfigValueError) as cm:
      check_config(required, actual, RequiredDeviceConfigMode.THROW)
    error_msg = str(cm.exception)
    self.assertIn(
        "settings.secure.immersive_mode_confirmations: "
        "got 'null', expected 'confirmed'.", error_msg)
    self.assertIn(
        "device_config.accessibility/font_scale: "
        "got '2.0', expected '1.0'.", error_msg)
    self.assertIn(
        "device_config.runtime_native/flag_one: "
        "value was absent, expected '42'.", error_msg)
    self.assertIn("Use --required-device-config-mode=warn to bypass.",
                  error_msg)
    self.assertIn("Use --required-device-config-mode=set to set the values",
                  error_msg)

  def test_partial_match_same_section(self):
    """Verify that only mismatched keys in a section are reported as errors."""
    actual = {
        "settings": {
            "secure": {
                "key_matching": "val1",
                "key_mismatching": "actual_val",
            },
        },
    }
    required = {
        "settings": {
            "secure": {
                "key_matching": "val1",
                "key_mismatching": "expected_val",
            },
        },
    }
    with self.assertRaises(DeviceConfigValueError) as cm:
      check_config(required, actual, RequiredDeviceConfigMode.THROW)
    error_msg = str(cm.exception)
    self.assertIn(
        "settings.secure.key_mismatching: got 'actual_val', "
        "expected 'expected_val'.", error_msg)
    self.assertNotIn("key_matching", error_msg)

  def test_check_device_config_invalid_mode(self):
    """Verify that invalid modes raise DeviceConfigValueError."""
    actual = {"key": "val1"}
    required = {"key": "val2"}
    with self.assertRaises(DeviceConfigValueError):
      check_config(
          required,
          actual,
          mode="invalid",  # type: ignore
      )

  def test_base_platform_device_config_empty(self):
    """Verify that base Platform returns an empty device config dictionary."""
    platform = mock.create_autospec(Platform, instance=True)
    platform.device_config.side_effect = (
        lambda: Platform.device_config(platform))
    self.assertEqual(platform.device_config(), {})

  def test_android_device_config_parsing(self):
    """Verify parsing of Android settings, getprop, and device_config."""
    platform, mock_adb = self._create_mock_android_platform()
    mock_adb.shell_stdout.side_effect = [
        ("accessibility/font_scale=1.0\n"
         "accessibility/color_inversion=0\n"
         "  runtime_native/flag_one = 42  \n"
         "top_level_flag=true\n"
         "ignored_line_without_equals\n"
         "=ignored_empty_key\n"),
        ("[ro.product.model]: [Pixel 10]\n"
         "[ro.build.version.sdk]: [34]\n"
         "[ro.build.version.base_os]: []\n"
         "[]: [ignored_empty_key]\n"
         "[unclosed_bracket: [value]\n"
         "[unbracketed_val]: raw_value\n"
         "invalid_line\n"),
        ("\n"
         "stay_on_while_plugged_in=3\n"
         "  whitespace_key  =  whitespace_value  \n"
         "multi_equal=a=b=c\n"
         "ignored_line_without_equals\n"
         "=ignored_empty_key\n"
         "empty_value=\n"),
        "immersive_mode_confirmations=confirmed\n",
        "screen_brightness=100\n",
    ]

    config = platform.device_config()
    self.assertEqual(
        config,
        {
            "android": {
                "device_config": {
                    "accessibility/font_scale": "1.0",
                    "accessibility/color_inversion": "0",
                    "runtime_native/flag_one": "42",
                    "top_level_flag": "true",
                },
                "getprop": {
                    "ro.product.model": "Pixel 10",
                    "ro.build.version.sdk": "34",
                    "ro.build.version.base_os": "",
                },
                "settings": {
                    "global": {
                        "stay_on_while_plugged_in": "3",
                        "whitespace_key": "whitespace_value",
                        "multi_equal": "a=b=c",
                        "empty_value": "",
                    },
                    "secure": {
                        "immersive_mode_confirmations": "confirmed",
                    },
                    "system": {
                        "screen_brightness": "100",
                    },
                },
            },
        },
    )
    mock_adb.shell_stdout.assert_has_calls([
        mock.call("cmd", "device_config", "list"),
        mock.call("getprop"),
        mock.call("settings", "list", "global"),
        mock.call("settings", "list", "secure"),
        mock.call("settings", "list", "system"),
    ])
    self.assertEqual(mock_adb.shell_stdout.call_count, 5)

  def test_android_system_details(self):
    """Verify that Android platform details include getprop properties."""
    platform, mock_adb = self._create_mock_android_platform()
    mock_adb.shell_stdout.return_value = ("[ro.product.model]: [Pixel 10]\n"
                                          "[ro.build.version.sdk]: [34]\n"
                                          "invalid_line\n")

    details = platform.system_details()
    mock_adb.shell_stdout.assert_called_once_with("getprop")
    self.assertEqual(
        details["Android"],
        {
            "ro.product.model": "Pixel 10",
            "ro.build.version.sdk": "34",
        },
    )

  def test_android_device_config_error_handling(self):
    """Verify that adb command errors propagate as SubprocessError."""
    platform, mock_adb = self._create_mock_android_platform()
    proc = subprocess.CompletedProcess(
        args=["adb", "shell"], returncode=1, stderr=b"device offline")
    mock_adb.shell_stdout.side_effect = SubprocessError(platform, proc)

    with self.assertRaises(SubprocessError):
      platform.device_config()

  def test_boolean_in_config_raises(self):
    """Verify that boolean values in required config fail to parse."""
    required = {"device_config": {"activity_manager/flag1": True}}
    self.assert_parse_raises(
        required, "device_config.activity_manager/flag1: Invalid config:")

  def test_integer_in_config_raises(self):
    """Verify that integer values in required config fail to parse."""
    required = {"settings": {"global": {"stay_on_while_plugged_in": 15}}}
    self.assert_parse_raises(
        required, "settings.global.stay_on_while_plugged_in: Invalid config:")

  def test_benchmark_required_device_config_class_var(self):
    """Verify Benchmark.REQUIRED_DEVICE_CONFIG class variable behavior."""

    class CustomBenchmark(Benchmark):
      NAME = "mock"
      DEFAULT_STORY_CLS = MockStory
      REQUIRED_DEVICE_CONFIG = {"android": {"key": "val"}}

    self.assertIsNone(Benchmark.REQUIRED_DEVICE_CONFIG)
    self.assertEqual(CustomBenchmark.REQUIRED_DEVICE_CONFIG,
                     {"android": {
                         "key": "val",
                     }})
    mock_story = MockStory("story_1")
    b = CustomBenchmark([mock_story])
    self.assertEqual(b.REQUIRED_DEVICE_CONFIG, {"android": {"key": "val"}})

  def test_required_device_config_mode_parse(self):
    """Verify parsing strings into RequiredDeviceConfigMode enum values."""
    self.assertIs(
        RequiredDeviceConfigMode.parse("throw"), RequiredDeviceConfigMode.THROW)
    self.assertIs(
        RequiredDeviceConfigMode.parse("THROW"), RequiredDeviceConfigMode.THROW)
    self.assertIs(
        RequiredDeviceConfigMode.parse("warn"), RequiredDeviceConfigMode.WARN)
    self.assertIs(
        RequiredDeviceConfigMode.parse(RequiredDeviceConfigMode.WARN),
        RequiredDeviceConfigMode.WARN)
    with self.assertRaises(argparse.ArgumentTypeError):
      RequiredDeviceConfigMode.parse("unknown")

  def test_any_of_predicate_matches_absent_value(self):
    """Verify a list requirement matches an absent value via 'null'."""
    check_config({"key": ["null", "1.0"]}, {}, RequiredDeviceConfigMode.THROW)

  def test_any_of_predicate_matches_first_alternative(self):
    """Verify a list requirement matches its first alternative."""
    check_config({"key": ["null", "1.0"]}, {"key": "null"},
                 RequiredDeviceConfigMode.THROW)

  def test_any_of_predicate_matches_later_alternative(self):
    """Verify a list requirement matches an alternative after the first."""
    check_config({"key": ["null", "1.0"]}, {"key": "1.0"},
                 RequiredDeviceConfigMode.THROW)

  def test_any_of_predicate_matches_single_alternative(self):
    """Verify a single-item list requirement behaves like a bare value."""
    check_config({"key": ["1.0"]}, {"key": "1.0"},
                 RequiredDeviceConfigMode.THROW)

  def test_any_of_predicate_rejects_single_alternative_mismatch(self):
    """Verify a single-item list requirement still reports a discrepancy."""
    self.assert_check_raises({"key": ["1.0"]}, {"key": "2.0"},
                             "key: got '2.0', expected any of ('1.0').")

  def test_any_of_predicate_matches_nested_list(self):
    """Verify a nested requirement list means the same as a flat one."""
    required = {"key": ["zero", ["one", "two"]]}
    for actual in ("zero", "one", "two"):
      with self.subTest(actual=actual):
        check_config(required, {"key": actual}, RequiredDeviceConfigMode.THROW)

  def test_any_of_predicate_rejects_nested_list_mismatch(self):
    """Verify a nested requirement list is described in the discrepancy."""
    required = {"key": ["zero", ["one", "two"]]}
    self.assert_check_raises(
        required, {"key": "three"},
        "key: got 'three', expected any of ('zero', any of ('one', 'two')).")

  def test_any_of_predicate_rejects_other_values(self):
    """Verify a list requirement rejects a value matching no alternative."""
    self.assert_check_raises({"key": ["null", "1.0"]}, {"key": "0.5"},
                             "key: got '0.5', expected any of ('null', '1.0').")

  def test_any_of_predicate_rejects_absent_value(self):
    """Verify a list requirement without 'null' rejects an absent value."""
    self.assert_check_raises(
        {"key": ["1.0", "2.0"]}, {},
        "key: value was absent, expected any of ('1.0', '2.0').")

  def test_any_of_predicate_rejects_invalid_mapping_item(self):
    """Verify error on a mapping with unknown keys in a requirement list."""
    required = {"key": ["valid", {"nested": "value"}]}
    self.assert_parse_raises(
        required, "key: Invalid config: unknown or conflicting keys "
        "['nested'].")

  def test_any_of_predicate_rejects_empty_list(self):
    """Verify error on empty requirement list."""
    self.assert_parse_raises({"key": []},
                             "key: Invalid empty requirement list: [].")

  def test_empty_mapping_is_empty_section(self):
    """Verify an empty requirement mapping imposes no requirements."""
    required = {"settings": {"system": {"key": {}}}}
    check_config(required, {}, RequiredDeviceConfigMode.THROW)

  def test_regex_predicate_matches_full_value(self):
    """Verify a regex requirement matches when the whole value matches."""
    required = {"key": {"$regex": r"1[4-6](\..*)?"}}
    for version in ("14", "15.1"):
      with self.subTest(version=version):
        check_config(required, {"key": version}, RequiredDeviceConfigMode.THROW)

  def test_regex_predicate_rejects_partial_match(self):
    """Verify a regex requirement is not satisfied by a substring match."""
    required = {"key": {"$regex": r"1[4-6](\..*)?"}}
    self.assert_check_raises(
        required, {"key": "114"},
        r"key: got '114', expected a full match for pattern '1[4-6](\..*)?'.")

  def test_regex_predicate_rejects_non_matching_value(self):
    """Verify a discrepancy when the value does not match the pattern."""
    required = {"key": {"$regex": r"1[4-6](\..*)?"}}
    self.assert_check_raises(
        required, {"key": "13"},
        r"key: got '13', expected a full match for pattern '1[4-6](\..*)?'.")

  def test_regex_predicate_rejects_absent_value(self):
    """Verify a discrepancy when the value is absent."""
    required = {"key": {"$regex": r"1[4-6](\..*)?"}}
    self.assert_check_raises(
        required, {}, r"key: value was absent, "
        r"expected a full match for pattern '1[4-6](\..*)?'.")

  def test_any_of_predicate_matches_regex_alternative(self):
    """Verify requirement list mixing a regex with an exact string."""
    required = {"key": [{"$regex": r"auto.*"}, "manual"]}
    for value in ("auto_mode", "manual"):
      with self.subTest(value=value):
        check_config(required, {"key": value}, RequiredDeviceConfigMode.THROW)

  def test_any_of_predicate_rejects_regex_alternative_mismatch(self):
    """Verify a discrepancy describing a regex alternative."""
    required = {"key": [{"$regex": r"auto.*"}, "manual"]}
    self.assert_check_raises(
        required, {"key": "unknown"}, "key: got 'unknown', expected any of "
        "(a full match for pattern 'auto.*', 'manual').")

  def test_numeric_range_predicate_matches_within_bounds(self):
    """Verify {$min: '...', $max: '...'} requirement."""
    required = {"key": {"$min": "50", "$max": "100"}}
    for value in ("50", "75.5", "100"):
      with self.subTest(value=value):
        check_config(required, {"key": value}, RequiredDeviceConfigMode.THROW)

  def test_numeric_range_predicate_rejects_below_lower_bound(self):
    """Verify a discrepancy when the value is under the lower bound."""
    required = {"key": {"$min": "50", "$max": "100"}}
    self.assert_check_raises(
        required, {"key": "49"},
        "key: got '49', expected numeric value between 50.0 and 100.0.")

  def test_numeric_range_predicate_rejects_above_upper_bound(self):
    """Verify a discrepancy when the value is over the upper bound."""
    required = {"key": {"$min": "50", "$max": "100"}}
    self.assert_check_raises(
        required, {"key": "101"},
        "key: got '101', expected numeric value between 50.0 and 100.0.")

  def test_numeric_range_predicate_rejects_non_numeric_value(self):
    """Verify a discrepancy when the value is not a number at all."""
    required = {"key": {"$min": "50", "$max": "100"}}
    self.assert_check_raises(
        required, {"key": "not_a_number"},
        "key: got 'not_a_number', expected numeric value between 50.0 "
        "and 100.0.")

  def test_numeric_range_predicate_matches_above_min(self):
    """Verify {$min: '...'} requirement without $max."""
    required = {"key": {"$min": "30"}}
    check_config(required, {"key": "30"}, RequiredDeviceConfigMode.THROW)

  def test_numeric_range_predicate_rejects_below_min(self):
    """Verify a discrepancy against a lower bound with no upper bound."""
    required = {"key": {"$min": "30"}}
    self.assert_check_raises(
        required, {"key": "29.9"},
        "key: got '29.9', expected numeric value >= 30.0.")

  def test_numeric_range_predicate_matches_below_max(self):
    """Verify {$max: '...'} requirement without $min."""
    required = {"key": {"$max": "60"}}
    for value in ("59.9", "60.0"):
      with self.subTest(value=value):
        check_config(required, {"key": value}, RequiredDeviceConfigMode.THROW)

  def test_numeric_range_predicate_rejects_above_max(self):
    """Verify a discrepancy against an upper bound with no lower bound."""
    required = {"key": {"$max": "60"}}
    self.assert_check_raises(required, {"key": "120"},
                             "key: got '120', expected numeric value <= 60.0.")

  def test_numeric_range_predicate_matches_exponent_notation(self):
    """Verify exponent notation is accepted for actual values."""
    required = {"key": {"$min": "5", "$max": "15"}}
    check_config(required, {"key": "1e1"}, RequiredDeviceConfigMode.THROW)

  def test_numeric_range_predicate_rejects_absent_value(self):
    """Verify discrepancy when actual value is absent for numeric range."""
    required = {"key": {"$min": "10"}}
    self.assert_check_raises(
        required, {}, "key: value was absent, expected numeric value >= 10.0.")

  def test_numeric_range_predicate_rejects_mapping_value(self):
    """Verify discrepancy when actual value is a mapping for numeric range."""
    required = {"key": {"$min": "10"}}
    actual = {"key": {"nested": "value"}}
    self.assert_check_raises(
        required, actual,
        "key: got {'nested': 'value'}, expected numeric value >= 10.0.")

  def test_numeric_range_predicate_rejects_nan_value(self):
    """Verify NaN never satisfies a two-sided numeric range."""
    # NaN compares False against every bound, so a range check written in
    # negative form would accept it, even with both bounds specified.
    required = {"key": {"$min": "0", "$max": "10"}}
    for actual in ("nan", "NaN", "-nan"):
      with self.subTest(actual=actual):
        self.assert_check_raises(
            required, {"key": actual}, f"key: got {actual!r}, "
            "expected numeric value between 0.0 and 10.0.")

  def test_numeric_range_predicate_rejects_nan_value_against_one_bound(self):
    """Verify NaN fails a one-sided numeric range rather than passing it."""
    required = {"key": {"$min": "0"}}
    self.assert_check_raises(required, {"key": "nan"},
                             "key: got 'nan', expected numeric value >= 0.0.")

  def test_any_of_predicate_matches_range_alternative(self):
    """Verify a requirement list whose alternative is a numeric range."""
    required = {"key": ["null", {"$max": "60"}]}
    for actual in ({"key": "null"}, {}, {"key": "60"}):
      with self.subTest(actual=actual):
        check_config(required, actual, RequiredDeviceConfigMode.THROW)

  def test_any_of_predicate_rejects_range_alternative_mismatch(self):
    """Verify a discrepancy describing a numeric range alternative."""
    required = {"key": ["null", {"$max": "60"}]}
    self.assert_check_raises(
        required, {"key": "120"},
        "key: got '120', expected any of ('null', numeric value <= 60.0).")

  def test_any_of_predicate_matches_mixed_alternatives(self):
    """Verify requirement list mixing a regex, a string and a range."""
    required = {"key": [{"$regex": r"auto.*"}, "manual", {"$min": "10"}]}
    for value in ("auto_mode", "manual", "15"):
      with self.subTest(value=value):
        check_config(required, {"key": value}, RequiredDeviceConfigMode.THROW)

  def test_any_of_predicate_rejects_mixed_alternatives_mismatch(self):
    """Verify a discrepancy describing every mixed alternative."""
    required = {"key": [{"$regex": r"auto.*"}, "manual", {"$min": "10"}]}
    for value in ("5", "unknown"):
      with self.subTest(value=value):
        self.assert_check_raises(
            required, {"key": value}, f"key: got {value!r}, expected any of "
            "(a full match for pattern 'auto.*', 'manual', "
            "numeric value >= 10.0).")

  def test_predicate_mapping_rejects_conflicting_keys(self):
    """Verify error on keys owned by different predicate forms."""
    required = {"key": {"$regex": "1", "$min": "1"}}
    self.assert_parse_raises(
        required,
        "key: Invalid config: unknown or conflicting keys ['$regex', '$min'].")

  def test_numeric_range_predicate_rejects_min_above_max(self):
    """Verify error when min is greater than max."""
    required = {"key": {"$min": "100", "$max": "50"}}
    self.assert_parse_raises(required,
                             "key: $min (100.0) cannot exceed $max (50.0).")

  def test_numeric_range_predicate_rejects_null_bounds(self):
    """Verify a null bound fails an assertion, even beside a valid one."""
    for bounds in ({"$min": None}, {"$min": None, "$max": "5"}):
      with self.subTest(bounds=bounds), self.assertRaises(AssertionError):
        parse_inline({"platform": {"key": bounds}})

  def test_numeric_range_predicate_accepts_unquoted_bounds(self):
    """Verify unquoted numeric bounds are read like quoted ones."""
    required = {"key": {"$min": 5, "$max": 15}}
    check_config(required, {"key": "10"}, RequiredDeviceConfigMode.THROW)

  def test_numeric_range_predicate_rejects_non_scalar_bound(self):
    """Verify error when a bound is neither a number nor a string."""
    required = {"key": {"$min": ["1"]}}
    self.assert_parse_raises(required, "key: could not convert string to float")

  def test_numeric_range_predicate_rejects_non_numeric_min(self):
    """Verify error when min string is not a valid number."""
    required = {"key": {"$min": "abc"}}
    self.assert_parse_raises(required,
                             "key: could not convert string to float: 'abc'")

  def test_numeric_range_predicate_rejects_non_numeric_max(self):
    """Verify error when max string is not a valid number."""
    required = {"key": {"$max": "xyz"}}
    self.assert_parse_raises(required,
                             "key: could not convert string to float: 'xyz'")

  def test_predicate_mapping_rejects_unknown_key(self):
    """Verify error when unknown keys are in predicate dictionary."""
    required = {"key": {"$regex": "foo", "unknown_opt": "bar"}}
    self.assert_parse_raises(
        required, "key: Invalid config: unknown or conflicting keys "
        "['$regex', 'unknown_opt'].")

  def test_regex_predicate_rejects_non_string(self):
    """Verify error when a regex pattern is not a string."""
    required = {"key": {"$regex": 5}}
    self.assert_parse_raises(required,
                             "key: Invalid $regex: expected str, got 5.")

  def test_regex_predicate_rejects_null_pattern(self):
    """Verify a null operator value fails an assertion."""
    with self.assertRaises(AssertionError):
      parse_inline({"platform": {"key": {"$regex": None}}})

  def test_regex_predicate_rejects_invalid_syntax(self):
    """Verify error when regex string has invalid syntax."""
    self.assert_parse_raises({"key": {"$regex": "["}}, "key: Invalid $regex:")

  def test_predicate_mapping_rejects_empty_mapping_in_list(self):
    """Verify error on empty mapping within requirement list."""
    self.assert_parse_raises({"key": ["valid", {}]},
                             "key: Invalid empty configuration mapping.")

  def test_predicate_mapping_rejects_unknown_operator(self):
    """Verify error when a mistyped operator is used."""
    required = {"key": {"$rgex": "foo"}}
    self.assert_parse_raises(
        required, "key: Invalid config: unknown or conflicting keys "
        "['$rgex'].")

  def test_section_key_may_shadow_an_operator_name(self):
    """Verify a setting named like an operator stays a section key."""
    required = {"getprop": {"regex": "abc"}}
    actual = {"getprop": {"regex": "abc"}}
    check_config(required, actual, RequiredDeviceConfigMode.THROW)

  def test_section_key_shadowing_an_operator_reports_discrepancy(self):
    """Verify a setting named like an operator is compared by value."""
    required = {"getprop": {"regex": "abc"}}
    actual = {"getprop": {"regex": "other"}}
    self.assert_check_raises(required, actual,
                             "getprop.regex: got 'other', expected 'abc'.")

  def test_actual_config_rejects_an_operator_prefixed_key(self):
    """Verify a device config key may not start with the operator prefix."""
    required = {"getprop": {"key": "abc"}}
    actual = {"getprop": {"$key": "abc"}}
    with self.assertRaises(AssertionError):
      check_config(required, actual, RequiredDeviceConfigMode.WARN)


class DeviceConfigTargetTestCase(unittest.TestCase):
  """Tests for the targets that requirements name, explicitly or not."""

  def target_of(self, required: Any) -> str | None:
    """Returns the target of a requirement placed at a single key."""
    parsed = parse_inline({"platform": {"key": required}})
    (requirement,) = parsed.platforms["platform"]
    return requirement.target

  def assert_parse_raises(self, required: Any, expected_message: str) -> None:
    """Assert that parsing a requirement at a single key raises."""
    with self.assertRaises(DeviceConfigError) as cm:
      self.target_of(required)
    self.assertIn(expected_message, str(cm.exception))

  def assert_parse_asserts(self, required: Any) -> None:
    """Assert that parsing a requirement at a single key fails an assertion."""
    with self.assertRaises(AssertionError):
      self.target_of(required)

  def test_exact_value_is_its_own_target(self):
    """Verify an exact string requirement targets that string."""
    self.assertEqual(self.target_of("1.0"), "1.0")

  def test_null_value_targets_deletion(self):
    """Verify a 'null' requirement targets deleting the setting."""
    self.assertEqual(self.target_of("null"), "null")

  def test_empty_value_is_its_own_target(self):
    """Verify an empty string requirement targets the empty string."""
    self.assertEqual(self.target_of(""), "")

  def test_explicit_empty_target(self):
    """Verify an explicit empty target is kept, not treated as absent."""
    self.assertEqual(self.target_of({"$regex": ".*", "$target": ""}), "")

  def test_regex_without_target_has_none(self):
    """Verify a regex requirement has no implicit target."""
    self.assertIsNone(self.target_of({"$regex": "a.*"}))

  def test_numeric_range_without_target_has_none(self):
    """Verify a numeric range requirement has no implicit target."""
    self.assertIsNone(self.target_of({"$min": "10"}))

  def test_regex_with_explicit_target(self):
    """Verify a regex requirement takes its explicit target."""
    required = {"$regex": "a.*", "$target": "abc"}
    self.assertEqual(self.target_of(required), "abc")

  def test_numeric_range_with_explicit_target(self):
    """Verify a numeric range requirement takes its explicit target."""
    required = {"$min": "10", "$max": "20", "$target": "15"}
    self.assertEqual(self.target_of(required), "15")

  def test_list_takes_first_value_target(self):
    """Verify a list requirement takes the target of its first item."""
    self.assertEqual(self.target_of(["1.0", "null"]), "1.0")

  def test_list_takes_first_null_target(self):
    """Verify a list whose first item is 'null' targets deletion."""
    self.assertEqual(self.target_of(["null", "1.0"]), "null")

  def test_list_takes_first_explicit_target(self):
    """Verify a list takes the explicit target of a first mapping item."""
    required = [{"$min": "10", "$target": "15"}, "auto"]
    self.assertEqual(self.target_of(required), "15")

  def test_list_takes_nested_first_target(self):
    """Verify a nested first item supplies the target of its own list."""
    required = [["one", "two"], "three"]
    self.assertEqual(self.target_of(required), "one")

  def test_list_without_first_target_has_none(self):
    """Verify later items never supply a target the first item lacks."""
    self.assertIsNone(self.target_of([{"$regex": "a.*"}, "manual"]))

  def test_explicit_target_does_not_change_matching(self):
    """Verify an explicit target leaves what is accepted unchanged."""
    required = {"key": {"$min": "10", "$target": "15"}}
    check_config(required, {"key": "12"}, RequiredDeviceConfigMode.THROW)
    with self.assertRaises(DeviceConfigValueError) as cm:
      check_config(required, {"key": "5"}, RequiredDeviceConfigMode.THROW)
    self.assertIn("key: got '5', expected numeric value >= 10.0.",
                  str(cm.exception))

  def test_null_target_failing_regex_asserts(self):
    """Verify deletion is not a valid target for a regex."""
    # A regex only ever matches present values, so deleting cannot meet it.
    self.assert_parse_asserts({"$regex": "(null)?", "$target": "null"})

  def test_target_alone_asserts(self):
    """Verify a target must accompany an operator."""
    self.assert_parse_asserts({"$target": "1.0"})

  def test_non_string_target_asserts(self):
    """Verify a target must be a string."""
    self.assert_parse_asserts({"$min": "10", "$target": 15})

  def test_null_target_asserts(self):
    """Verify a null target is rejected rather than read as absent."""
    self.assert_parse_asserts({"$min": "10", "$target": None})

  def test_target_failing_regex_asserts(self):
    """Verify a target must match the pattern it accompanies."""
    self.assert_parse_asserts({"$regex": "a.*", "$target": "bcd"})

  def test_target_failing_numeric_range_asserts(self):
    """Verify a target must fall within the range it accompanies."""
    self.assert_parse_asserts({"$min": "10", "$max": "20", "$target": "25"})

  def test_null_target_failing_numeric_range_asserts(self):
    """Verify deletion is not a valid target for a numeric range."""
    self.assert_parse_asserts({"$min": "10", "$target": "null"})

  def test_target_failing_in_list_item_asserts(self):
    """Verify a target is validated inside a requirement list too."""
    self.assert_parse_asserts(["auto", {"$min": "10", "$target": "5"}])

  def test_target_with_unknown_operator_raises(self):
    """Verify a target does not mask a misspelled operator."""
    required = {"$rgex": "a.*", "$target": "abc"}
    self.assert_parse_raises(
        required, "key: Invalid config: unknown or conflicting keys "
        "['$rgex'].")

  def test_target_with_conflicting_operators_raises(self):
    """Verify a target does not mask operators of different forms."""
    required = {"$regex": "1", "$min": "1", "$target": "1"}
    self.assert_parse_raises(
        required, "key: Invalid config: unknown or conflicting keys "
        "['$regex', '$min'].")


class PlatformDeviceConfigWriterTestCase(unittest.TestCase):
  """Tests for the base Platform's device config writing."""

  def test_set_raises(self):
    """Verify the base Platform refuses to write any key."""
    platform = mock.create_autospec(Platform, instance=True)
    key_path = ("settings", "system", "screen_brightness")
    with self.assertRaises(ValueError) as cm:
      Platform.set_device_config_value(platform, key_path, "100")
    self.assertIn(
        "Cannot set device config 'settings.system.screen_brightness'",
        str(cm.exception))


class AndroidDeviceConfigWriterTestCase(unittest.TestCase):
  """Tests for writing single device config values on Android."""

  def setUp(self) -> None:
    super().setUp()
    self.adb = mock.Mock()
    self.platform = mock.create_autospec(AndroidAdbPlatform, instance=True)
    self.platform.adb = self.adb

  def set_value(self, key_path: tuple[str, ...], value: str | None) -> None:
    AndroidAdbPlatform.set_device_config_value(self.platform, key_path, value)

  def test_set_settings_in_every_namespace(self):
    """Verify every settings namespace is writable."""
    for namespace in ("global", "secure", "system"):
      with self.subTest(namespace=namespace):
        self.adb.reset_mock()
        self.set_value(("settings", namespace, "key"), "1")
        self.adb.shell.assert_called_once_with("settings", "put", namespace,
                                               "key", "1")

  def test_set_unsupported_key_paths_raises(self):
    """Verify writing an unsupported key raises without touching adb."""
    for key_path in (
        ("getprop", "ro.product.model"),
        ("settings", "unknown", "key"),
        ("settings", "system", ""),
        ("settings", "system"),
        ("settings", "system", "key", "extra"),
        ("device_config", "flag_without_namespace"),
        ("device_config", "/key"),
        ("device_config", "namespace/"),
        ("device_config", "namespace", "key"),
        ("cmd", "uimode"),
        (),
    ):
      with self.subTest(key_path=key_path), self.assertRaisesRegex(
          ValueError, "Cannot set device config"):
        self.set_value(key_path, "1")
    self.adb.shell.assert_not_called()

  def test_delete_settings_value(self):
    """Verify a None settings value is deleted with 'settings delete'."""
    self.set_value(("settings", "global", "animator_duration_scale"), None)
    self.adb.shell.assert_called_once_with("settings", "delete", "global",
                                           "animator_duration_scale")

  def test_set_empty_settings_value(self):
    """Verify an empty value is written rather than deleted."""
    self.set_value(("settings", "secure", "key"), "")
    self.adb.shell.assert_called_once_with("settings", "put", "secure", "key",
                                           "")

  def test_set_literal_null_settings_value(self):
    """Verify a "null" string is written as is, rather than deleted."""
    self.set_value(("settings", "secure", "key"), "null")
    self.adb.shell.assert_called_once_with("settings", "put", "secure", "key",
                                           "null")

  def test_set_device_config_value(self):
    """Verify a device_config flag is written with 'device_config put'."""
    self.set_value(("device_config", "accessibility/font_scale"), "1.0")
    self.adb.shell.assert_called_once_with("cmd", "device_config", "put",
                                           "accessibility", "font_scale", "1.0")

  def test_delete_device_config_value(self):
    """Verify a None flag is deleted with 'device_config delete'."""
    self.set_value(("device_config", "accessibility/font_scale"), None)
    self.adb.shell.assert_called_once_with("cmd", "device_config", "delete",
                                           "accessibility", "font_scale")

  def test_set_device_config_key_with_slash(self):
    """Verify only the first '/' separates the namespace from the key."""
    self.set_value(("device_config", "namespace/sub/key"), "1")
    self.adb.shell.assert_called_once_with("cmd", "device_config", "put",
                                           "namespace", "sub/key", "1")

  def test_set_propagates_adb_errors(self):
    """Verify adb command failures propagate as SubprocessError."""
    proc = subprocess.CompletedProcess(
        args=["adb", "shell"], returncode=1, stderr=b"device offline")
    self.adb.shell.side_effect = SubprocessError(self.platform, proc)
    with self.assertRaises(SubprocessError):
      self.set_value(("settings", "system", "screen_brightness"), "100")


class DeviceConfigSetterTestCase(unittest.TestCase):
  """Tests for setting device config to meet requirements, and restoring."""

  BRIGHTNESS = ("settings", "system", "screen_brightness")
  TIMEOUT = ("settings", "system", "screen_off_timeout")
  PEAK_REFRESH = ("settings", "system", "peak_refresh_rate")
  FONT_SCALE = ("device_config", "accessibility/font_scale")

  # Requirements that INITIAL fails, so apply() writes both.
  TWO_CHANGES: dict[DeviceConfigKeyPath, Any] = {
      BRIGHTNESS: "100",
      FONT_SCALE: "1.0",
  }

  INITIAL: dict[str, Any] = {
      "settings": {
          "system": {
              "screen_brightness": "50",
              "screen_off_timeout": "30000",
          },
      },
      "device_config": {
          "accessibility/font_scale": "2.0",
      },
  }

  def setUp(self) -> None:
    super().setUp()
    self.platform = LinuxMockPlatform()
    self.platform.device_config_data = copy.deepcopy(self.INITIAL)
    self.config = self.platform.device_config_data
    self.writes = self.platform.device_config_writes

  def setter(self, required: dict[DeviceConfigKeyPath,
                                  Any]) -> DeviceConfigSetter:
    """Returns a setter for requirements keyed by key path."""
    nested: dict[str, Any] = {}
    for key_path, value in required.items():
      node = nested
      for key in key_path[:-1]:
        node = node.setdefault(key, {})
      node[key_path[-1]] = value
    name = self.platform.name
    requirements = parse_inline({name: nested}).platforms
    return DeviceConfigSetter(self.platform, requirements[name])

  def assert_apply_raises(
      self,
      setter: DeviceConfigSetter,
      exception: type[BaseException] = DeviceConfigValueError,
      regex: str = "") -> str:
    """Asserts that apply() raises, and returns the error message."""
    with self.assertRaisesRegex(exception, regex) as cm:
      setter.apply()
    return str(cm.exception)

  def assert_unchanged(self) -> None:
    """Asserts that the device config is in its initial state."""
    self.assertEqual(self.config, self.INITIAL)

  @contextlib.contextmanager
  def failing_write(self, key_path: DeviceConfigKeyPath, value: str | None,
                    error: BaseException) -> Iterator[None]:
    """Makes writing value to key_path raise error."""
    real_set = self.platform.set_device_config_value

    def set_or_raise(path: DeviceConfigKeyPath, val: str | None) -> None:
      if (path, val) == (key_path, value):
        self.writes.append((path, val))
        raise error
      real_set(path, val)

    with mock.patch.object(
        self.platform, "set_device_config_value", side_effect=set_or_raise):
      yield

  @contextlib.contextmanager
  def freeze_reads(self) -> Iterator[None]:
    """Makes device_config() always return the initial config."""
    with mock.patch.object(
        self.platform,
        "device_config",
        return_value={self.platform.name: self.INITIAL}):
      yield

  def test_no_discrepancies_writes_nothing(self):
    """Verify a device meeting every requirement is left untouched."""
    self.setter({self.BRIGHTNESS: "50"}).apply()
    self.assertEqual(self.writes, [])

  def test_apply_writes_only_failing_requirements(self):
    """Verify only requirements the device fails are written."""
    self.setter({
        self.BRIGHTNESS: "100",
        self.TIMEOUT: {
            "$min": "10000",
            "$target": "1800000",
        },
    }).apply()
    self.assertEqual(self.writes, [(self.BRIGHTNESS, "100")])
    self.assertEqual(self.config["settings"]["system"], {
        "screen_brightness": "100",
        "screen_off_timeout": "30000",
    })

  def test_restore_writes_originals_in_reverse_order(self):
    """Verify restore() undoes every change, last change first."""
    setter = self.setter(self.TWO_CHANGES)
    setter.apply()
    self.writes.clear()
    self.assertEqual(setter.restore(), [])
    self.assertEqual(self.writes, [(self.FONT_SCALE, "2.0"),
                                   (self.BRIGHTNESS, "50")])
    self.assert_unchanged()

  def test_restore_twice_does_nothing(self):
    """Verify each change is restored at most once."""
    setter = self.setter({self.BRIGHTNESS: "100"})
    setter.apply()
    setter.restore()
    self.writes.clear()
    self.assertEqual(setter.restore(), [])
    self.assertEqual(self.writes, [])

  def test_restore_deletes_setting_that_was_absent(self):
    """Verify a setting added by apply() is deleted again on restore."""
    key_path = ("settings", "system", "new_key")
    setter = self.setter({key_path: "1"})
    setter.apply()
    self.assertEqual(self.config["settings"]["system"]["new_key"], "1")
    setter.restore()
    self.assert_unchanged()

  def test_restore_writes_back_literal_null(self):
    """Verify a setting whose value is the string 'null' is restored as is."""
    self.config["settings"]["system"]["peak_refresh_rate"] = "null"
    setter = self.setter({self.PEAK_REFRESH: "60"})
    setter.apply()
    setter.restore()
    self.assertEqual(self.writes[-1], (self.PEAK_REFRESH, "null"))
    self.assertEqual(self.config["settings"]["system"]["peak_refresh_rate"],
                     "null")

  def test_null_target_deletes_setting(self):
    """Verify a 'null' requirement is met by deleting the setting."""
    setter = self.setter({self.FONT_SCALE: "null"})
    setter.apply()
    self.assertEqual(self.writes, [(self.FONT_SCALE, None)])
    self.assertNotIn("accessibility/font_scale", self.config["device_config"])
    setter.restore()
    self.assert_unchanged()

  def test_requirement_without_target_raises(self):
    """Verify a requirement without $target raises, after other writes."""
    setter = self.setter({
        self.BRIGHTNESS: "100",
        self.TIMEOUT: {
            "$min": "1800000",
        },
    })
    message = self.assert_apply_raises(setter)
    self.assertIn(
        "  - settings.system.screen_off_timeout: got '30000', "
        "expected numeric value >= 1800000.0.", message)
    self.assertIn((self.BRIGHTNESS, "100"), self.writes)
    setter.restore()
    self.assert_unchanged()

  def test_write_failure_stops_apply(self):
    """Verify a failed write stops apply(), and restore() undoes the rest."""
    setter = self.setter(self.TWO_CHANGES)
    with self.failing_write(self.FONT_SCALE, "1.0", RuntimeError("denied")):
      self.assert_apply_raises(setter, RuntimeError, "denied")
    setter.restore()
    # The failed write is not restored, as it is not known to have happened.
    self.assertEqual(self.writes, [(self.BRIGHTNESS, "100"),
                                   (self.FONT_SCALE, "1.0"),
                                   (self.BRIGHTNESS, "50")])
    self.assert_unchanged()

  def test_ineffective_write_raises(self):
    """Verify a write that did not take effect raises."""
    setter = self.setter(self.TWO_CHANGES)
    with self.freeze_reads():
      message = self.assert_apply_raises(setter)
    self.assertIn(
        "  - device_config.accessibility/font_scale: got '2.0', "
        "expected '1.0'.", message)
    self.assertNotIn("--required-device-config-mode", message)
    setter.restore()
    self.assert_unchanged()

  def test_restore_failure_is_returned_and_others_restored(self):
    """Verify a failed restore is returned without stopping the others."""
    setter = self.setter(self.TWO_CHANGES)
    setter.apply()
    with self.failing_write(self.BRIGHTNESS, "50", RuntimeError("offline")), \
        self.assertLogs(level=logging.ERROR):
      failures = setter.restore()
    self.assertEqual(failures, ["settings.system.screen_brightness: offline"])
    self.assertEqual(self.config["device_config"]["accessibility/font_scale"],
                     "2.0")
    self.assertEqual(self.config["settings"]["system"]["screen_brightness"],
                     "100")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
