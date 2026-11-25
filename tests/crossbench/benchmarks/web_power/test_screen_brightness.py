# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import unittest
from typing import override
from unittest import mock

from crossbench import path as pth
from crossbench.benchmarks.web_power.screen_brightness import (
  ScreenBrightnessLookup,
  ScreenBrightnessResolver,
)
from crossbench.browsers.attributes import BrowserAttributes
from crossbench.cli.subcommand.describe import get_all_config_classes
from crossbench.config import ConfigError
from crossbench.env.runner_env import ValidationMode
from crossbench.runner.runner import Runner
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.benchmarks.web_power.test_base import (
  BaseWebPowerBenchmarkTestCase,
  MockWebPowerBenchmark,
  MockWebPowerStory,
)
from tests.crossbench.mock_helper import (
  AndroidAdbMockPlatform,
  LinuxMockPlatform,
)


class ScreenBrightnessLookupTestCase(unittest.TestCase):
  def test_registered_in_describe_configs(self) -> None:
    config_classes = get_all_config_classes()

    self.assertIn(ScreenBrightnessLookup, config_classes)

  def test_invalid_entries_raise(self) -> None:
    invalid_cases: tuple[tuple[object, str], ...] = (
      ({"Pixel 10.*": 28}, "brightness mapping for"),
      ({"Pixel 10.*": {}}, "brightness mapping for"),
      ({"Pixel 10.*": {"0": 28}}, "target nits"),
      ({"Pixel 10.*": {"200": 33, "0200": 30}}, "Duplicate target nits 200"),
      ({"Pixel 10.*": {"200": -1}}, "brightness setting"),
    )
    for raw_config, expected_msg in invalid_cases:
      with self.subTest(raw_config=raw_config):
        with self.assertRaisesRegex(argparse.ArgumentTypeError, expected_msg):
          ScreenBrightnessLookup.parse(raw_config)

  def test_shipped_mapping_defines_default_target_nits(self) -> None:
    lookup = ScreenBrightnessLookup.load_default()

    self.assertGreater(len(lookup), 0)
    for levels in lookup.values():
      self.assertIn(ScreenBrightnessResolver.DEFAULT_TARGET_NITS, levels)
    mapped_levels = lookup.resolve("Pixel 9 Pro XL")
    assert mapped_levels is not None
    mapped_device_brightness = mapped_levels[
      ScreenBrightnessResolver.DEFAULT_TARGET_NITS
    ]
    self.assertIsInstance(mapped_device_brightness, int)
    self.assertGreaterEqual(mapped_device_brightness, 1)
    self.assertLessEqual(mapped_device_brightness, 255)
    self.assertIsNone(lookup.resolve("Unmapped Device Model"))


class WebPowerScreenBrightnessCliTestCase(BaseWebPowerBenchmarkTestCase):
  @property
  @override
  def benchmark_cls(self) -> type[MockWebPowerBenchmark]:
    return MockWebPowerBenchmark

  def test_kwargs_from_cli_default(self) -> None:
    args = self.parse_args("--site", "cnn")

    kwargs = MockWebPowerBenchmark.kwargs_from_cli(args)

    self.assertIsNone(kwargs["screen_brightness"])

  def test_kwargs_from_cli_custom_value(self) -> None:
    args = self.parse_args("--site", "cnn", "--screen-brightness=2468")

    kwargs = MockWebPowerBenchmark.kwargs_from_cli(args)

    self.assertEqual(kwargs["screen_brightness"], 2468)

  def test_kwargs_from_cli_negative_value_raises(self) -> None:
    with self.assertRaisesRegex(argparse.ArgumentError, "--screen-brightness"):
      self.parse_args("--site=cnn", "--screen-brightness=-1")


class WebPowerScreenBrightnessSetupTestCase(CrossbenchFakeFsTestCase):
  def setUp(self) -> None:
    super().setUp()
    self.fs.add_real_file(MockWebPowerBenchmark.device_config_path())
    self.host_platform = LinuxMockPlatform()
    self.android_platform = AndroidAdbMockPlatform(
      self.host_platform,
      "emulator-5554",
      adb=mock.MagicMock(build_type="user"),
    )
    self.android_platform.use_mock_name = False
    self.android_platform.device_config_data = {
      "settings": {
        "secure": {},
        "global": {},
        "system": {
          "screen_brightness_mode": "1",
          "screen_brightness": "128",
        },
      },
      "device_config": {},
    }

  def _write_public_mapping(
    self, contents: str = '{"Public Model.*": {"200": 33}}'
  ) -> None:
    self.fs.create_file(ScreenBrightnessLookup.public_path(), contents=contents)

  def _setup_device_config(
    self,
    model: str = "Public Model Pro",
    screen_brightness: int | None = None,
    use_android: bool = True,
  ) -> None:
    story = MockWebPowerStory.from_site("cnn")
    benchmark = MockWebPowerBenchmark(
      stories=[story], screen_brightness=screen_brightness
    )
    browser = mock.MagicMock()
    browser.unique_name = "mock_browser"
    browser.driver_logging = False
    browser.label = "mock_label"
    browser.platform = (
      self.android_platform if use_android else self.host_platform
    )
    browser.attributes.return_value = BrowserAttributes.CHROMIUM_BASED
    runner = Runner(
      out_dir=pth.LocalPath("/tmp/out"),
      browsers=[browser],
      benchmark=benchmark,
      disabled_probes=["perfetto"],
      env_validation_mode=ValidationMode.SKIP,
      in_memory_result_db=True,
    )
    with mock.patch.object(
      AndroidAdbMockPlatform,
      "model",
      new_callable=mock.PropertyMock,
      return_value=model,
    ):
      runner._setup_device_config()

  def _current_brightness(self) -> str:
    return self.android_platform.device_config_data["settings"]["system"][
      "screen_brightness"
    ]

  def test_mapped_public_model_writes_mode_before_brightness(self) -> None:
    self._write_public_mapping()

    self._setup_device_config(model="Public Model Pro")

    self.assertEqual(self._current_brightness(), "33")
    written_keys = [
      key_path for key_path, _ in self.android_platform.device_config_writes
    ]
    self.assertEqual(
      written_keys.count(("settings", "system", "screen_brightness")), 1
    )
    mode_idx = written_keys.index(
      ("settings", "system", "screen_brightness_mode")
    )
    brightness_idx = written_keys.index(
      ("settings", "system", "screen_brightness")
    )
    self.assertLess(mode_idx, brightness_idx)

  def test_mapped_internal_model_merges_with_public(self) -> None:
    self._write_public_mapping()
    self.fs.create_file(
      ScreenBrightnessLookup.internal_path(),
      contents='{"Internal Device.*": {"200": 28}}',
    )

    self._setup_device_config(model="Internal Device Pro")

    self.assertEqual(self._current_brightness(), "28")

  def test_unmapped_model_logs_warning_and_falls_back_to_one(self) -> None:
    self._write_public_mapping()

    with self.assertLogs(level="WARNING") as cm:
      self._setup_device_config(model="Unknown Device")

    output = "\n".join(cm.output)
    self.assertEqual(self._current_brightness(), "1")
    self.assertIn("Unknown Device", output)
    self.assertIn("--screen-brightness", output)

  def test_missing_200_nit_entry_falls_back_to_one(self) -> None:
    self._write_public_mapping('{"Other Nit Model": {"100": 20}}')

    with self.assertLogs(level="WARNING") as cm:
      self._setup_device_config(model="Other Nit Model")

    self.assertEqual(self._current_brightness(), "1")
    self.assertIn("Other Nit Model", "\n".join(cm.output))

  def test_cli_override_skips_mapping_file_and_overrides_unmapped(self) -> None:
    self._setup_device_config(model="Unknown Device", screen_brightness=100)

    self.assertEqual(self._current_brightness(), "100")

  def test_non_android_platform_skips_mapping_file(self) -> None:
    self._setup_device_config(use_android=False)

    self.assertEqual(self.host_platform.device_config_writes, [])

  def test_cli_override_on_non_android_platform_raises(self) -> None:
    with self.assertRaisesRegex(
      ConfigError, "--screen-brightness is only supported on Android"
    ):
      self._setup_device_config(screen_brightness=50, use_android=False)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
