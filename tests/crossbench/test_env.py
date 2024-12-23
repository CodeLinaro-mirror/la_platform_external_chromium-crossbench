# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
import unittest
from unittest import mock

import hjson

from crossbench.env import (HostEnvironment, HostEnvironmentConfig,
                            ValidationError, ValidationMode)
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


class HostEnvironmentConfigTestCase(unittest.TestCase):

  def test_combine_bool_value(self):
    default = HostEnvironmentConfig()
    self.assertIsNone(default.power_use_battery)

    battery = HostEnvironmentConfig(power_use_battery=True)
    self.assertTrue(battery.power_use_battery)
    self.assertTrue(battery.merge(battery).power_use_battery)
    self.assertTrue(default.merge(battery).power_use_battery)
    self.assertTrue(battery.merge(default).power_use_battery)

    power = HostEnvironmentConfig(power_use_battery=False)
    self.assertFalse(power.power_use_battery)
    self.assertFalse(power.merge(power).power_use_battery)
    self.assertFalse(default.merge(power).power_use_battery)
    self.assertFalse(power.merge(default).power_use_battery)

    with self.assertRaises(ValueError):
      power.merge(battery)

  def test_combine_min_float_value(self):
    default = HostEnvironmentConfig()
    self.assertIsNone(default.cpu_min_relative_speed)

    high = HostEnvironmentConfig(cpu_min_relative_speed=1)
    self.assertEqual(high.cpu_min_relative_speed, 1)
    self.assertEqual(high.merge(high).cpu_min_relative_speed, 1)
    self.assertEqual(default.merge(high).cpu_min_relative_speed, 1)
    self.assertEqual(high.merge(default).cpu_min_relative_speed, 1)

    low = HostEnvironmentConfig(cpu_min_relative_speed=0.5)
    self.assertEqual(low.cpu_min_relative_speed, 0.5)
    self.assertEqual(low.merge(low).cpu_min_relative_speed, 0.5)
    self.assertEqual(default.merge(low).cpu_min_relative_speed, 0.5)
    self.assertEqual(low.merge(default).cpu_min_relative_speed, 0.5)

    self.assertEqual(high.merge(low).cpu_min_relative_speed, 1)

  def test_combine_max_float_value(self):
    default = HostEnvironmentConfig()
    self.assertIsNone(default.cpu_max_usage_percent)

    high = HostEnvironmentConfig(cpu_max_usage_percent=100)
    self.assertEqual(high.cpu_max_usage_percent, 100)
    self.assertEqual(high.merge(high).cpu_max_usage_percent, 100)
    self.assertEqual(default.merge(high).cpu_max_usage_percent, 100)
    self.assertEqual(high.merge(default).cpu_max_usage_percent, 100)

    low = HostEnvironmentConfig(cpu_max_usage_percent=0)
    self.assertEqual(low.cpu_max_usage_percent, 0)
    self.assertEqual(low.merge(low).cpu_max_usage_percent, 0)
    self.assertEqual(default.merge(low).cpu_max_usage_percent, 0)
    self.assertEqual(low.merge(default).cpu_max_usage_percent, 0)

    self.assertEqual(high.merge(low).cpu_max_usage_percent, 0)

  def test_parse_example_config_file(self):
    example_config_file = pathlib.Path(
        __file__).parent.parent / "config/doc/env.config.hjson"
    if not example_config_file.exists():
      raise unittest.SkipTest(f"Test file {example_config_file} does not exist")
    with example_config_file.open(encoding="utf-8") as f:
      data = hjson.load(f)
    HostEnvironmentConfig(**data["env"])


class HostEnvironmentTestCase(CrossbenchFakeFsTestCase):

  def setUp(self):
    super().setUp()
    self.mock_platform = mock.Mock()
    self.mock_platform.processes.return_value = []
    self.out_dir = pathlib.Path("results/current_benchmark_run_results")
    self.fs.create_file(self.out_dir)
    self.mock_runner = mock.Mock(
        platform=self.mock_platform,
        repetitions=1,
        probes=[],
        browsers=[],
        out_dir=self.out_dir)

  def create_env(self, *args, **kwargs) -> HostEnvironment:
    return HostEnvironment(self.mock_platform, self.mock_runner.out_dir,
                           self.mock_runner.browsers, self.mock_runner.probes,
                           self.mock_runner.repetitions, *args, **kwargs)

  def test_instantiate(self):
    env = self.create_env()
    self.assertEqual(env.platform, self.mock_platform)

    config = HostEnvironmentConfig()
    env = self.create_env(config)
    self.assertSequenceEqual(env.browsers, self.mock_runner.browsers)
    self.assertEqual(env.config, config)

  def test_warn_mode_skip(self):
    config = HostEnvironmentConfig()
    env = self.create_env(config, ValidationMode.SKIP)
    env.handle_warning("foo")

  def test_warn_mode_fail(self):
    config = HostEnvironmentConfig()
    env = self.create_env(config, ValidationMode.THROW)
    with self.assertRaises(ValidationError) as cm:
      env.handle_warning("custom env check warning")
    self.assertIn("custom env check warning", str(cm.exception))

  def test_warn_mode_prompt(self):
    config = HostEnvironmentConfig()
    env = self.create_env(config, ValidationMode.PROMPT)
    with mock.patch("builtins.input", return_value="Y") as cm:
      env.handle_warning("custom env check warning")
    cm.assert_called_once()
    self.assertIn("custom env check warning", cm.call_args[0][0])
    with mock.patch("builtins.input", return_value="n") as cm:
      with self.assertRaises(ValidationError):
        env.handle_warning("custom env check warning")
    cm.assert_called_once()
    self.assertIn("custom env check warning", cm.call_args[0][0])

  def test_warn_mode_warn(self):
    config = HostEnvironmentConfig()
    env = self.create_env(config, ValidationMode.WARN)
    with mock.patch("logging.warning") as cm:
      env.handle_warning("custom env check warning")
    cm.assert_called_once()
    self.assertIn("custom env check warning", cm.call_args[0][0])

  def test_validate_skip(self):
    env = self.create_env(HostEnvironmentConfig(), ValidationMode.SKIP)
    env.validate()

  def test_validate_warn(self):
    env = self.create_env(HostEnvironmentConfig(), ValidationMode.WARN)
    with mock.patch("logging.warning") as cm:
      env.validate()
    cm.assert_not_called()
    self.mock_platform.sh_stdout.assert_not_called()
    self.mock_platform.sh.assert_not_called()

  def test_validate_warn_no_probes(self):
    env = self.create_env(
        HostEnvironmentConfig(require_probes=True), ValidationMode.WARN)
    with mock.patch("logging.warning") as cm:
      env.validate()
    cm.assert_called_once()
    self.mock_platform.sh_stdout.assert_not_called()
    self.mock_platform.sh.assert_not_called()

  def test_request_battery_power_on(self):
    env = self.create_env(
        HostEnvironmentConfig(power_use_battery=True), ValidationMode.THROW)
    self.mock_platform.is_battery_powered = True
    env.validate()

    self.mock_platform.is_battery_powered = False
    with self.assertRaises(Exception) as cm:
      env.validate()
    self.assertIn("battery", str(cm.exception).lower())

  def test_request_battery_power_off(self):
    env = self.create_env(
        HostEnvironmentConfig(power_use_battery=False), ValidationMode.THROW)
    self.mock_platform.is_battery_powered = True
    with self.assertRaises(ValidationError) as cm:
      env.validate()
    self.assertIn("battery", str(cm.exception).lower())

    self.mock_platform.is_battery_powered = False
    env.validate()

  def test_request_battery_power_off_conflicting_probe(self):
    self.mock_platform.is_battery_powered = False

    mock_probe = mock.Mock()
    mock_probe.configure_mock(BATTERY_ONLY=True, name="mock_probe")
    self.mock_runner.probes = [mock_probe]
    env = self.create_env(
        HostEnvironmentConfig(power_use_battery=False), ValidationMode.THROW)

    with self.assertRaises(ValidationError) as cm:
      env.validate()
    message = str(cm.exception).lower()
    self.assertIn("mock_probe", message)
    self.assertIn("battery", message)

    mock_probe.BATTERY_ONLY = False
    env.validate()

  def test_request_is_headless_default(self):
    env = self.create_env(
        HostEnvironmentConfig(browser_is_headless=HostEnvironmentConfig.IGNORE),
        ValidationMode.THROW)
    mock_browser = mock.Mock(platform=self.mock_platform)
    self.mock_runner.browsers = [mock_browser]

    mock_browser.viewport.is_headless = False
    env.validate()

    mock_browser.viewport.is_headless = True
    env.validate()

  def test_request_is_headless_true(self):
    mock_browser = mock.Mock(
        platform=self.mock_platform, path=pathlib.Path("bin/browser_a"))
    self.mock_runner.browsers = [mock_browser]
    env = self.create_env(
        HostEnvironmentConfig(browser_is_headless=True), ValidationMode.THROW)

    self.mock_platform.has_display = True
    mock_browser.viewport.is_headless = False
    with self.assertRaises(ValidationError) as cm:
      env.validate()
    self.assertIn("is_headless", str(cm.exception))

    self.mock_platform.has_display = False
    with self.assertRaises(ValidationError) as cm:
      env.validate()

    self.mock_platform.has_display = True
    mock_browser.viewport.is_headless = True
    env.validate()

    self.mock_platform.has_display = False
    env.validate()

  def test_request_is_headless_false(self):
    mock_browser = mock.Mock(
        platform=self.mock_platform, path=pathlib.Path("bin/browser_a"))
    self.mock_runner.browsers = [mock_browser]
    env = self.create_env(
        HostEnvironmentConfig(browser_is_headless=False), ValidationMode.THROW)

    self.mock_platform.has_display = True
    mock_browser.viewport.is_headless = False
    env.validate()

    self.mock_platform.has_display = False
    with self.assertRaises(ValidationError) as cm:
      env.validate()

    self.mock_platform.has_display = True
    mock_browser.viewport.is_headless = True
    with self.assertRaises(ValidationError) as cm:
      env.validate()
    self.assertIn("is_headless", str(cm.exception))

  def test_results_dir_single(self):
    env = self.create_env()
    with mock.patch("logging.warning") as cm:
      env.validate()
    cm.assert_not_called()

  def test_results_dir_non_existent(self):
    self.mock_runner.out_dir = pathlib.Path("does/not/exist")
    env = self.create_env()
    with mock.patch("logging.warning") as cm:
      env.validate()
    cm.assert_not_called()

  def test_results_dir_many(self):
    # Create fake test result dirs:
    for i in range(30):
      (self.out_dir.parent / str(i)).mkdir()
    env = self.create_env()
    with mock.patch("logging.warning") as cm:
      env.validate()
    cm.assert_called_once()

  def test_results_dir_too_many(self):
    # Create fake test result dirs:
    for i in range(100):
      (self.out_dir.parent / str(i)).mkdir()
    env = self.create_env()
    with mock.patch("logging.error") as cm:
      env.validate()
    cm.assert_called_once()

  def test_check_installed_missing(self):

    def which_none(_):
      return None

    self.mock_platform.which = which_none
    env = self.create_env()
    with self.assertRaises(ValidationError) as cm:
      env.check_installed(["custom_binary"])
    self.assertIn("custom_binary", str(cm.exception))
    with self.assertRaises(ValidationError) as cm:
      env.check_installed(["custom_binary_a", "custom_binary_b"])
    self.assertIn("custom_binary_a", str(cm.exception))
    self.assertIn("custom_binary_b", str(cm.exception))

  def test_check_installed_partially_missing(self):

    def which_custom(binary):
      if binary == "custom_binary_b":
        return "/bin/custom_binary_b"
      return None

    self.mock_platform.which = which_custom
    env = self.create_env()
    env.check_installed(["custom_binary_b"])
    with self.assertRaises(ValidationError) as cm:
      env.check_installed(["custom_binary_a", "custom_binary_b"])
    self.assertIn("custom_binary_a", str(cm.exception))
    self.assertNotIn("custom_binary_b", str(cm.exception))


class ValidationModeTestCase(unittest.TestCase):

  def test_construct(self):
    self.assertIs(ValidationMode("throw"), ValidationMode.THROW)
    self.assertIs(ValidationMode("THROW"), ValidationMode.THROW)
    self.assertIs(ValidationMode("prompt"), ValidationMode.PROMPT)
    self.assertIs(ValidationMode("PROMPT"), ValidationMode.PROMPT)
    self.assertIs(ValidationMode("warn"), ValidationMode.WARN)
    self.assertIs(ValidationMode("WARN"), ValidationMode.WARN)
    self.assertIs(ValidationMode("skip"), ValidationMode.SKIP)
    self.assertIs(ValidationMode("SKIP"), ValidationMode.SKIP)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
