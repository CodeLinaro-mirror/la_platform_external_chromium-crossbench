# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import unittest
from typing import Any
from unittest import mock

from crossbench import path as pth
from crossbench.benchmarks.base import Benchmark
from crossbench.device_config import DeviceConfigError, DeviceConfigMap, \
    RequiredDeviceConfigMode, check_device_config, \
    parse_required_device_config
from crossbench.plt.android_adb import AndroidAdbPlatform
from crossbench.plt.base import Platform, SubprocessError
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.mock_helper import MockStory


def check_config(required: DeviceConfigMap, actual: DeviceConfigMap,
                 mode: RequiredDeviceConfigMode) -> None:
  """Parses one platform's requirements and checks them, as the runner does."""
  parsed = parse_required_device_config({"platform": required})
  check_device_config(parsed["platform"], actual, mode)


class DeviceConfigParserTestCase(CrossbenchFakeFsTestCase):
  """Tests for parsing device configuration files and mappings."""

  def test_parse_mapping(self):
    """Verify that a mapping input is parsed into platform requirements."""
    config = {"android": {"key": "val"}}
    self.assertEqual(list(parse_required_device_config(config)), ["android"])

  def test_parse_lowercases_top_level_keys(self):
    """Verify that top-level platform keys are normalized to lower case."""
    config = {"Android": {"key": "val"}, "MacOS": {"other": "val2"}}
    required = parse_required_device_config(config)
    self.assertEqual(sorted(required), ["android", "macos"])

  def test_parse_empty_platform_section(self):
    """Verify an empty platform section imposes no requirements."""
    # An empty section is the only way to state "nothing is required here".
    self.assertEqual(
        parse_required_device_config({"android": {}}), {"android": ()})

  def test_parse_empty_subsection_adds_no_requirements(self):
    """Verify an empty subsection contributes nothing beside a real one."""
    config = {"android": {"settings": {}, "key": "val"}}
    required = parse_required_device_config(config)
    self.assertEqual(len(required["android"]), 1)

  def test_parse_non_mapping_platform_section_raises(self):
    """Verify DeviceConfigError when a platform section is not a mapping."""
    with self.assertRaises(DeviceConfigError) as cm:
      parse_required_device_config({"android": "val"})
    self.assertIn("android: Invalid platform section", str(cm.exception))

  def test_parse_valid_json_file(self):
    """Verify that parse_required_device_config correctly parses JSON files."""
    path = pth.LocalPath("/config.json")
    self.fs.create_file(path, contents=json.dumps({"android": {"key": "val"}}))
    self.assertEqual(list(parse_required_device_config(path)), ["android"])

  def test_parse_valid_hjson_file(self):
    """Verify that parse_required_device_config correctly parses Hjson files."""
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
    self.assertEqual(list(parse_required_device_config(path)), ["android"])

  def test_parse_missing_file_raises(self):
    """Verify FileNotFoundError when config file does not exist."""
    path = pth.LocalPath("/nonexistent.json")
    with self.assertRaises(FileNotFoundError):
      parse_required_device_config(path)

  def test_parse_invalid_json_raises(self):
    """Verify ValueError when parsing invalid Hjson/JSON content."""
    path = pth.LocalPath("/invalid.hjson")
    self.fs.create_file(path, contents="{not-json")
    with self.assertRaises(ValueError):
      parse_required_device_config(path)

  def test_parse_duplicate_keys_raises(self):
    """Verify ValueError when parsing config with duplicate keys."""
    path = pth.LocalPath("/duplicate.hjson")
    self.fs.create_file(path, contents='{"key": 1, "key": 2}')
    with self.assertRaises(ValueError):
      parse_required_device_config(path)

  def test_parse_non_mapping_file_raises(self):
    """Verify DeviceConfigError when config file content is not a mapping."""
    path = pth.LocalPath("/list.json")
    self.fs.create_file(path, contents='["not", "a", "mapping"]')
    with self.assertRaises(DeviceConfigError) as cm:
      parse_required_device_config(path)
    self.assertIn("Invalid config type", str(cm.exception))

    scalar_path = pth.LocalPath("/scalar.json")
    self.fs.create_file(scalar_path, contents='"just_a_string"')
    with self.assertRaises(DeviceConfigError) as cm:
      parse_required_device_config(scalar_path)
    self.assertIn("Invalid config type", str(cm.exception))

  def test_parse_invalid_type_raises(self):
    """Verify DeviceConfigError when input is neither mapping nor path."""
    with self.assertRaises(DeviceConfigError) as cm:
      parse_required_device_config(12345)  # type: ignore
    self.assertIn("Invalid config type", str(cm.exception))

  def test_parse_string_path_raises(self):
    """Verify that passing a string path raises DeviceConfigError."""
    with self.assertRaises(DeviceConfigError) as cm:
      parse_required_device_config("/config.json")  # type: ignore
    self.assertIn("Invalid config type", str(cm.exception))

  def test_parse_validates_requirements(self):
    """Verify DeviceConfigError on a malformed requirement."""
    config = {"android": {"settings": {"key": 5}}}
    with self.assertRaises(DeviceConfigError) as cm:
      parse_required_device_config(config)
    self.assertIn("android: settings.key: Invalid config: 5.",
                  str(cm.exception))

  def test_parse_validates_requirements_from_file(self):
    """Verify DeviceConfigError on a malformed requirement in a file."""
    path = pth.LocalPath("/invalid_requirement.json")
    self.fs.create_file(path, contents=json.dumps({"android": {"key": 5}}))
    with self.assertRaises(DeviceConfigError) as cm:
      parse_required_device_config(path)
    self.assertIn("android: key: Invalid config: 5.", str(cm.exception))

  def test_parse_validates_other_platform_sections(self):
    """Verify requirements are validated for every platform, not just one."""
    config = {"android": {"key": "val"}, "macos": {"key": 5}}
    with self.assertRaises(DeviceConfigError) as cm:
      parse_required_device_config(config)
    self.assertIn("macos: key: Invalid config: 5.", str(cm.exception))


class DeviceConfigTestCase(unittest.TestCase):
  """Tests for device configuration comparison and platform querying."""

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
    with self.assertRaises(DeviceConfigError) as cm:
      check_config(required, actual, RequiredDeviceConfigMode.THROW)
    self.assertIn(expected_message, str(cm.exception))

  def assert_parse_raises(self, required: Any, expected_message: str) -> None:
    """Assert that parsing the requirements raises the expected error."""
    with self.assertRaises(ValueError) as cm:
      parse_required_device_config({"platform": required})
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
    """Verify that value mismatches raise DeviceConfigError in THROW mode."""
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
    with self.assertRaises(DeviceConfigError) as cm:
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
    with self.assertRaises(DeviceConfigError) as cm:
      check_config(required, actual, RequiredDeviceConfigMode.THROW)
    error_msg = str(cm.exception)
    self.assertIn(
        "settings.secure.key_mismatching: got 'actual_val', "
        "expected 'expected_val'.", error_msg)
    self.assertNotIn("key_matching", error_msg)

  def test_check_device_config_invalid_mode(self):
    """Verify that invalid modes raise DeviceConfigError."""
    actual = {"key": "val1"}
    required = {"key": "val2"}
    with self.assertRaises(DeviceConfigError):
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
    """Verify that boolean values in required config raise ValueError."""
    required = {"device_config": {"activity_manager/flag1": True}}
    self.assert_parse_raises(
        required, "device_config.activity_manager/flag1: Invalid config:")

  def test_integer_in_config_raises(self):
    """Verify that integer values in required config raise ValueError."""
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

  def test_any_of_predicate_rejects_mapping_item(self):
    """Verify error on a mapping within a requirement list."""
    # Mappings denote subsections, so they are not valid list items.
    required = {"key": ["valid", {"nested": "value"}]}
    self.assert_parse_raises(required,
                             "key: Invalid config: {'nested': 'value'}.")

  def test_any_of_predicate_rejects_empty_list(self):
    """Verify error on empty requirement list."""
    self.assert_parse_raises({"key": []},
                             "key: Invalid empty requirement list: [].")

  def test_empty_mapping_is_empty_section(self):
    """Verify an empty requirement mapping imposes no requirements."""
    required = {"settings": {"system": {"key": {}}}}
    check_config(required, {}, RequiredDeviceConfigMode.THROW)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
