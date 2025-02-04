# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
import unittest
from typing import Any
from unittest import mock

from crossbench import plt
from crossbench.env import (EnvironmentConfig, HostEnvironment, ValidationError,
                            ValidationMode)
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.mock_helper import LinuxMockPlatform, MockPlatform


class HostEnvironmentTestCase(CrossbenchFakeFsTestCase):

  def setUp(self):
    super().setUp()
    self.platform = MockPlatform()
    self.platform.use_fs = True
    self.out_dir = pathlib.Path("results/current_benchmark_run_results")
    self.fs.create_dir(self.out_dir)
    self.mock_runner = mock.Mock(
        platform=plt.PLATFORM,
        repetitions=1,
        probes=[],
        browsers=[],
        out_dir=self.out_dir)

  def patch_property(self, target: Any, name: str, **kwargs):
    new_callable = kwargs.pop("new_callable", mock.PropertyMock)
    return mock.patch.object(
        type(target), name, new_callable=new_callable, **kwargs)

  def create_env(self, *args, **kwargs) -> HostEnvironment:
    return HostEnvironment(self.platform, self.mock_runner.out_dir,
                           self.mock_runner.browsers, self.mock_runner.probes,
                           self.mock_runner.repetitions, *args, **kwargs)

  def test_instantiate(self):
    env = self.create_env()
    self.assertEqual(env.platform, self.platform)

    config = EnvironmentConfig()
    env = self.create_env(config)
    self.assertSequenceEqual(env.browsers, self.mock_runner.browsers)
    self.assertEqual(env.config, config)

  def test_warn_mode_skip(self):
    config = EnvironmentConfig()
    env = self.create_env(config, ValidationMode.SKIP)
    env.handle_warning("foo")

  def test_warn_mode_fail(self):
    config = EnvironmentConfig()
    env = self.create_env(config, ValidationMode.THROW)
    with self.assertRaises(ValidationError) as cm:
      env.handle_warning("custom env check warning")
    self.assertIn("custom env check warning", str(cm.exception))

  def test_warn_mode_prompt(self):
    config = EnvironmentConfig()
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
    config = EnvironmentConfig()
    env = self.create_env(config, ValidationMode.WARN)
    with mock.patch("logging.warning") as cm:
      env.handle_warning("custom env check warning")
    cm.assert_called_once()
    self.assertIn("custom env check warning", cm.call_args[0][0])

  def test_validate_skip(self):
    env = self.create_env(EnvironmentConfig(), ValidationMode.SKIP)
    env.validate()

  def test_validate_warn(self):
    env = self.create_env(EnvironmentConfig(), ValidationMode.WARN)
    with mock.patch("logging.warning") as cm:
      env.validate()
    cm.assert_not_called()
    self.assertFalse(self.platform.sh_cmds)

  def test_validate_warn_no_probes(self):
    env = self.create_env(
        EnvironmentConfig(require_probes=True), ValidationMode.WARN)
    with mock.patch("logging.warning") as cm:
      env.validate()
    cm.assert_called_once()
    self.assertFalse(self.platform.sh_cmds)

  def test_request_battery_power_on(self):
    with self.patch_property(self.platform, "is_battery_powered") as mocked:
      env = self.create_env(
          EnvironmentConfig(power_use_battery=True), ValidationMode.THROW)
      mocked.return_value = True
      env.validate()

      mocked.return_value = False
      with self.assertRaises(Exception) as cm:
        env.validate()
      self.assertIn("battery", str(cm.exception).lower())

  def test_request_battery_power_off(self):
    env = self.create_env(
        EnvironmentConfig(power_use_battery=False), ValidationMode.THROW)
    with self.patch_property(self.platform,
                             "is_battery_powered") as is_battery_powered:
      is_battery_powered.return_value = True
      with self.assertRaises(ValidationError) as cm:
        env.validate()
      self.assertIn("battery", str(cm.exception).lower())
      self.assertEqual(is_battery_powered.call_count, 1)

      is_battery_powered.return_value = False
      env.validate()
      self.assertEqual(is_battery_powered.call_count, 2)

  def test_mock_request_battery_power_off(self):
    with self.patch_property(self.platform,
                             "is_battery_powered") as is_battery_powered:
      is_battery_powered.return_value = False
      self.assertFalse(self.platform.is_battery_powered)
      is_battery_powered.return_value = True
      self.assertTrue(self.platform.is_battery_powered)

  def test_request_battery_power_off_conflicting_probe(self):
    with self.patch_property(self.platform,
                             "is_battery_powered") as is_battery_powered:
      is_battery_powered.return_value = False

      mock_probe = mock.Mock()
      mock_probe.configure_mock(BATTERY_ONLY=True, name="mock_probe")
      self.mock_runner.probes = [mock_probe]
      env = self.create_env(
          EnvironmentConfig(power_use_battery=False), ValidationMode.THROW)

      with self.assertRaises(ValidationError) as cm:
        env.validate()
      message = str(cm.exception).lower()
      self.assertIn("mock_probe", message)
      self.assertIn("battery", message)

      mock_probe.BATTERY_ONLY = False
      env.validate()

  def test_request_is_headless_default(self):
    env = self.create_env(
        EnvironmentConfig(browser_is_headless=EnvironmentConfig.IGNORE),
        ValidationMode.THROW)
    mock_browser = mock.Mock(platform=self.platform)
    self.mock_runner.browsers = [mock_browser]

    mock_browser.viewport.is_headless = False
    env.validate()

    mock_browser.viewport.is_headless = True
    env.validate()

  def test_request_is_headless_true(self):
    mock_browser = mock.Mock(
        platform=self.platform, path=pathlib.Path("bin/browser_a"))
    self.mock_runner.browsers = [mock_browser]
    env = self.create_env(
        EnvironmentConfig(browser_is_headless=True), ValidationMode.THROW)

    with self.patch_property(self.platform, "has_display") as has_display:
      has_display.return_value = True
      mock_browser.viewport.is_headless = False
      with self.assertRaises(ValidationError) as cm:
        env.validate()
      self.assertIn("is_headless", str(cm.exception))

      has_display.return_value = False
      with self.assertRaises(ValidationError) as cm:
        env.validate()

      has_display.return_value = True
      mock_browser.viewport.is_headless = True
      env.validate()

      has_display.return_value = False
      env.validate()

  def test_request_is_headless_false(self):
    self.platform = LinuxMockPlatform()
    mock_browser = mock.Mock(
        platform=self.platform, path=pathlib.Path("bin/browser_a"))
    self.mock_runner.browsers = [mock_browser]
    env = self.create_env(
        EnvironmentConfig(browser_is_headless=False), ValidationMode.THROW)
    with self.patch_property(self.platform, "has_display") as has_display:
      has_display.return_value = True
      mock_browser.viewport.is_headless = False
      env.validate()

      has_display.return_value = False
      self.assertFalse(self.platform.has_display)
      with self.assertRaises(ValidationError) as cm:
        env.validate()

      has_display.return_value = True
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

    with mock.patch.object(
        self.platform, "which", side_effect=which_none) as mock_which:
      env = self.create_env()
      with self.assertRaises(ValidationError) as cm:
        env.check_installed(["custom_binary"])
      self.assertIn("custom_binary", str(cm.exception))
      with self.assertRaises(ValidationError) as cm:
        env.check_installed(["custom_binary_a", "custom_binary_b"])
      self.assertIn("custom_binary_a", str(cm.exception))
      self.assertIn("custom_binary_b", str(cm.exception))
      mock_which.assert_called()

  def test_check_installed_partially_missing(self):

    def which_custom(binary):
      if binary == "custom_binary_b":
        return "/bin/custom_binary_b"
      return None

    with mock.patch.object(
        self.platform, "which", side_effect=which_custom) as mock_which:
      env = self.create_env()
      env.check_installed(["custom_binary_b"])
      with self.assertRaises(ValidationError) as cm:
        env.check_installed(["custom_binary_a", "custom_binary_b"])
      self.assertIn("custom_binary_a", str(cm.exception))
      self.assertNotIn("custom_binary_b", str(cm.exception))
      mock_which.assert_called()


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
