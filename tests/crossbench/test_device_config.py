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
    RequiredDeviceConfigMode, check_device_config, parse_device_config
from crossbench.plt.android_adb import AndroidAdbPlatform
from crossbench.plt.base import Platform, SubprocessError
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.mock_helper import MockStory


class DeviceConfigParserTestCase(CrossbenchFakeFsTestCase):
  """Tests for parsing device configuration files and mappings."""

  def test_parse_mapping(self):
    """Verify that parse_device_config passes through mapping inputs."""
    config = {"android": {"key": "val"}}
    self.assertEqual(parse_device_config(config), config)

  def test_parse_lowercases_top_level_keys(self):
    """Verify that parse_device_config normalizes top-level keys to lower."""
    config = {"Android": {"key": "val"}, "MacOS": {"other": "val2"}}
    self.assertEqual(
        parse_device_config(config), {
            "android": {
                "key": "val"
            },
            "macos": {
                "other": "val2"
            }
        })

  def test_parse_valid_json_file(self):
    """Verify that parse_device_config correctly parses JSON files."""
    path = pth.LocalPath("/config.json")
    self.fs.create_file(path, contents=json.dumps({"android": {"key": "val"}}))
    self.assertEqual(parse_device_config(path), {"android": {"key": "val"}})

  def test_parse_valid_hjson_file(self):
    """Verify that parse_device_config correctly parses Hjson files."""
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
    self.assertEqual(parse_device_config(path), {"android": {"key": "val"}})

  def test_parse_missing_file_raises(self):
    """Verify FileNotFoundError when config file does not exist."""
    path = pth.LocalPath("/nonexistent.json")
    with self.assertRaises(FileNotFoundError):
      parse_device_config(path)

  def test_parse_invalid_json_raises(self):
    """Verify ValueError when parsing invalid Hjson/JSON content."""
    path = pth.LocalPath("/invalid.hjson")
    self.fs.create_file(path, contents="{not-json")
    with self.assertRaises(ValueError):
      parse_device_config(path)

  def test_parse_duplicate_keys_raises(self):
    """Verify ValueError when parsing config with duplicate keys."""
    path = pth.LocalPath("/duplicate.hjson")
    self.fs.create_file(path, contents='{"key": 1, "key": 2}')
    with self.assertRaises(ValueError):
      parse_device_config(path)

  def test_parse_non_mapping_file_raises(self):
    """Verify DeviceConfigError when config file content is not a mapping."""
    path = pth.LocalPath("/list.json")
    self.fs.create_file(path, contents='["not", "a", "mapping"]')
    with self.assertRaises(DeviceConfigError) as cm:
      parse_device_config(path)
    self.assertIn("Invalid config type", str(cm.exception))

    scalar_path = pth.LocalPath("/scalar.json")
    self.fs.create_file(scalar_path, contents='"just_a_string"')
    with self.assertRaises(DeviceConfigError) as cm:
      parse_device_config(scalar_path)
    self.assertIn("Invalid config type", str(cm.exception))

  def test_parse_invalid_type_raises(self):
    """Verify DeviceConfigError when input is neither mapping nor path."""
    with self.assertRaises(DeviceConfigError) as cm:
      parse_device_config(12345)  # type: ignore
    self.assertIn("Invalid config type", str(cm.exception))

  def test_parse_string_path_raises(self):
    """Verify that passing a string path raises DeviceConfigError."""
    with self.assertRaises(DeviceConfigError) as cm:
      parse_device_config("/config.json")  # type: ignore
    self.assertIn("Invalid config type", str(cm.exception))


class DeviceConfigTestCase(unittest.TestCase):
  """Tests for device configuration comparison and platform querying."""

  _REQUIRED_IMMERSIVE_CONFIRMED: DeviceConfigMap = {
      "settings": {
          "secure": {
              "immersive_mode_confirmations": "confirmed",
          },
      },
  }

  def assert_check_raises(
      self,
      required: Any,
      actual: Any,
      expected_message: str,
      exception_cls: type[Exception] = DeviceConfigError,
  ) -> None:
    """Assert that check_device_config raises the expected error."""
    with self.assertRaises(exception_cls) as cm:
      check_device_config(required, actual, RequiredDeviceConfigMode.THROW)
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
    check_device_config(config, config, RequiredDeviceConfigMode.THROW)

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
        "expected 'confirmed', got 'null'",
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
    check_device_config(required, actual, RequiredDeviceConfigMode.THROW)

  def test_absent_setting_fails_when_value_required(self):
    """Verify that absent settings raise when a concrete value is required."""
    self.assert_check_raises(
        self._REQUIRED_IMMERSIVE_CONFIRMED,
        {"settings": {
            "secure": {}
        }},
        "settings.secure.immersive_mode_confirmations: "
        "expected 'confirmed', but value was absent",
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
        "settings.secure: expected 'null', got {'some_setting': '1'}",
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
    check_device_config(required, actual, RequiredDeviceConfigMode.THROW)

  def test_missing_section_when_child_requires_value(self):
    """Verify error when parent section is absent but child needs a value."""
    # Section "secure" is completely absent from actual settings.
    self.assert_check_raises(
        self._REQUIRED_IMMERSIVE_CONFIRMED,
        {"settings": {}},
        "settings.secure.immersive_mode_confirmations: "
        "expected 'confirmed', but value was absent",
    )

  def test_top_level_section_missing(self):
    """Verify error when the actual configuration dictionary is empty."""
    self.assert_check_raises(
        self._REQUIRED_IMMERSIVE_CONFIRMED,
        {},
        "settings.secure.immersive_mode_confirmations: "
        "expected 'confirmed', but value was absent",
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
        "expected 'confirmed', but value was absent",
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
        "settings.secure.flag: expected '123', got 123",
    )

  def test_empty_required_config(self):
    """Verify that an empty required config matches any actual config."""
    check_device_config(
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
    check_device_config(
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
      check_device_config(
          self._REQUIRED_IMMERSIVE_CONFIRMED,
          actual,
          mode=RequiredDeviceConfigMode.WARN)
    self.assertTrue(
        any("settings.secure.immersive_mode_confirmations: "
            "expected 'confirmed', got 'null'." in log for log in cm.output))

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
      check_device_config(required, actual, mode=RequiredDeviceConfigMode.WARN)
    logs = "\n".join(cm.output)
    self.assertIn(
        "settings.secure.immersive_mode_confirmations: "
        "expected 'confirmed', got 'null'.", logs)
    self.assertIn(
        "settings.secure.another_key: "
        "expected 'val', but value was absent.", logs)

  def test_check_device_config_warn_mode_no_discrepancies(self):
    """Verify that no warnings are logged when configs match in WARN mode."""
    with self.assertNoLogs(level=logging.WARNING):
      check_device_config(
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
      check_device_config(required, actual, RequiredDeviceConfigMode.THROW)
    error_msg = str(cm.exception)
    self.assertIn(
        "settings.secure.immersive_mode_confirmations: "
        "expected 'confirmed', got 'null'", error_msg)
    self.assertIn(
        "device_config.accessibility/font_scale: "
        "expected '1.0', got '2.0'", error_msg)
    self.assertIn(
        "device_config.runtime_native/flag_one: "
        "expected '42', but value was absent", error_msg)
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
      check_device_config(required, actual, RequiredDeviceConfigMode.THROW)
    error_msg = str(cm.exception)
    self.assertIn(
        "settings.secure.key_mismatching: expected 'expected_val', "
        "got 'actual_val'", error_msg)
    self.assertNotIn("key_matching", error_msg)

  def test_check_device_config_invalid_mode(self):
    """Verify that invalid modes raise DeviceConfigError."""
    actual = {"key": "val1"}
    required = {"key": "val2"}
    with self.assertRaises(DeviceConfigError):
      check_device_config(
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
    actual = {
        "device_config": {
            "activity_manager/flag1": "true",
        },
    }
    required = {
        "device_config": {
            "activity_manager/flag1": True,
        },
    }
    self.assert_check_raises(
        required,
        actual,
        "Invalid config at device_config.activity_manager/flag1",
        exception_cls=ValueError,
    )

  def test_integer_in_config_raises(self):
    """Verify that integer values in required config raise ValueError."""
    actual = {
        "settings": {
            "global": {
                "stay_on_while_plugged_in": "15",
            },
        },
    }
    required = {
        "settings": {
            "global": {
                "stay_on_while_plugged_in": 15,
            },
        },
    }
    self.assert_check_raises(
        required,
        actual,
        "Invalid config at settings.global.stay_on_while_plugged_in",
        exception_cls=ValueError,
    )

  def test_benchmark_required_device_config_class_var(self):
    """Verify Benchmark.REQUIRED_DEVICE_CONFIG class variable behavior."""

    class CustomBenchmark(Benchmark):
      NAME = "mock"
      DEFAULT_STORY_CLS = MockStory
      REQUIRED_DEVICE_CONFIG = {"android": {"key": "val"}}

    self.assertIsNone(Benchmark.REQUIRED_DEVICE_CONFIG)
    self.assertEqual(CustomBenchmark.REQUIRED_DEVICE_CONFIG,
                     {"android": {
                         "key": "val"
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


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
