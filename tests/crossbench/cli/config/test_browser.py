# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import unittest

import hjson
from immutabledict import immutabledict

from crossbench import path as pth
from crossbench import plt
from crossbench.browsers.chrome.chrome import Chrome
from crossbench.cli.config.browser import BrowserConfig
from crossbench.cli.config.driver import BrowserDriverType, DriverConfig
from crossbench.cli.config.network import NetworkConfig, NetworkSpeedPreset
from crossbench.exception import MultiException
from crossbench.types import JsonDict
from tests import test_helper
from tests.crossbench import mock_browser
from tests.crossbench.cli.config.base import (ADB_DEVICES_OUTPUT,
                                              ADB_DEVICES_SINGLE_OUTPUT,
                                              XCTRACE_DEVICES_OUTPUT,
                                              XCTRACE_DEVICES_SINGLE_OUTPUT,
                                              BaseConfigTestCase)


class BrowserConfigTestCase(BaseConfigTestCase):

  def test_equal(self):
    path = Chrome.stable_path(self.platform)
    self.assertEqual(
        BrowserConfig(path, DriverConfig(BrowserDriverType.default())),
        BrowserConfig(path, DriverConfig(BrowserDriverType.default())))
    self.assertNotEqual(
        BrowserConfig(path, DriverConfig(BrowserDriverType.default())),
        BrowserConfig(
            path,
            DriverConfig(
                BrowserDriverType.default(), settings=immutabledict(custom=1))))
    self.assertNotEqual(
        BrowserConfig(path, DriverConfig(BrowserDriverType.default())),
        BrowserConfig(
            pth.AnyPath("foo"), DriverConfig(BrowserDriverType.default())))

  def test_hashable(self):
    _ = hash(BrowserConfig.default())
    _ = hash(
        BrowserConfig(
            pth.AnyPath("foo"),
            DriverConfig(
                BrowserDriverType.default(), settings=immutabledict(custom=1))))

  def test_parse_name_or_path(self):
    path = Chrome.stable_path(self.platform)
    self.assertEqual(
        BrowserConfig.parse("chrome"),
        BrowserConfig(path, DriverConfig(BrowserDriverType.default())))
    self.assertEqual(
        BrowserConfig.parse(str(path)),
        BrowserConfig(path, DriverConfig(BrowserDriverType.default())))

  def test_parse_invalid_name(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      BrowserConfig.parse("")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse("a-random-name")
    self.assertIn("a-random-name", str(cm.exception))

  def test_parse_invalid_path(self):
    path = pth.AnyPath("foo/bar")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse(str(path))
    self.assertIn(str(path), str(cm.exception))
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse("selenium/bar")
    self.assertIn("selenium", str(cm.exception))
    self.assertIn("bar", str(cm.exception))

  def test_parse_invalid_windows_path(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse("selenium\\bar")
    self.assertIn("selenium\\\\bar", str(cm.exception))
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse("C:\\selenium\\bar")
    self.assertIn("C:\\\\selenium\\\\bar", str(cm.exception))

  def test_parse_simple_missing_driver(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse(":chrome")
    self.assertIn("driver", str(cm.exception))

  def test_parse_invalid_network_preset(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse("selenium:chrome:1xx2")
    self.assertIn("network", str(cm.exception))
    self.assertIn("1xx2", str(cm.exception))

  def test_parse_simple_with_driver(self):
    self.assertEqual(
        BrowserConfig.parse("selenium:chrome"),
        BrowserConfig(
            Chrome.stable_path(self.platform),
            DriverConfig(BrowserDriverType.WEB_DRIVER)))
    self.assertEqual(
        BrowserConfig.parse("webdriver:chrome"),
        BrowserConfig(
            Chrome.stable_path(self.platform),
            DriverConfig(BrowserDriverType.WEB_DRIVER)))
    self.assertEqual(
        BrowserConfig.parse("applescript:chrome"),
        BrowserConfig(
            Chrome.stable_path(self.platform),
            DriverConfig(BrowserDriverType.APPLE_SCRIPT)))
    self.assertEqual(
        BrowserConfig.parse("osa:chrome"),
        BrowserConfig(
            Chrome.stable_path(self.platform),
            DriverConfig(BrowserDriverType.APPLE_SCRIPT)))

  def test_parse_simple_with_driver_with_network(self):
    self.assertEqual(
        BrowserConfig.parse("chrome:4G"),
        BrowserConfig(
            Chrome.stable_path(self.platform),
            DriverConfig(BrowserDriverType.WEB_DRIVER),
            NetworkConfig.parse_live(NetworkSpeedPreset.MOBILE_4G)))
    self.assertEqual(
        BrowserConfig.parse("selenium:chrome:4G"),
        BrowserConfig(
            Chrome.stable_path(self.platform),
            DriverConfig(BrowserDriverType.WEB_DRIVER),
            NetworkConfig.parse_live(NetworkSpeedPreset.MOBILE_4G)))

  def test_parse_simple_ambiguous_with_driver_ios(self):
    self.platform.sh_results = [XCTRACE_DEVICES_OUTPUT]
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = BrowserConfig.parse("ios:chrome")
    self.assertIn("devices", str(cm.exception))

  def test_parse_simple_with_driver_ios(self):
    self.platform.sh_results = [
        XCTRACE_DEVICES_SINGLE_OUTPUT, XCTRACE_DEVICES_SINGLE_OUTPUT
    ]
    config = BrowserConfig.parse("ios:chrome")
    self.assertEqual(
        config,
        BrowserConfig(
            Chrome.stable_path(self.platform),
            DriverConfig(BrowserDriverType.IOS)))
    self.assertIsNone(config.network)
    self.platform.sh_results = [
        XCTRACE_DEVICES_SINGLE_OUTPUT,
    ]
    config = BrowserConfig.parse("ios:chrome:live")
    self.assertEqual(config.network, NetworkConfig.default())

  def test_parse_simple_with_driver_ios_with_network(self):
    self.platform.sh_results = [
        XCTRACE_DEVICES_SINGLE_OUTPUT, XCTRACE_DEVICES_SINGLE_OUTPUT
    ]
    config = BrowserConfig.parse("ios:chrome:4G")
    self.assertEqual(
        config,
        BrowserConfig(
            Chrome.stable_path(self.platform),
            DriverConfig(BrowserDriverType.IOS),
            NetworkConfig.parse_live(NetworkSpeedPreset.MOBILE_4G)))
    self.assertEqual(config.network,
                     NetworkConfig.parse_live(NetworkSpeedPreset.MOBILE_4G))

  def test_parse_simple_ambiguous_with_driver_android(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = BrowserConfig.parse("adb:chrome")
    self.assertIn("devices", str(cm.exception))

  def test_parse_simple_with_driver_android(self):
    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]
    self.assertEqual(
        BrowserConfig.parse("adb:chrome"),
        BrowserConfig(
            pth.AnyPosixPath("com.android.chrome"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]
    self.assertEqual(
        BrowserConfig.parse("android:com.chrome.beta"),
        BrowserConfig(
            pth.AnyPosixPath("com.chrome.beta"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]
    self.assertEqual(
        BrowserConfig.parse("android:chrome-beta"),
        BrowserConfig(
            pth.AnyPosixPath("com.chrome.beta"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]
    self.assertEqual(
        BrowserConfig.parse("adb:chrome-dev"),
        BrowserConfig(
            pth.AnyPosixPath("com.chrome.dev"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]
    self.assertEqual(
        BrowserConfig.parse("android:chrome-canary"),
        BrowserConfig(
            pth.AnyPosixPath("com.chrome.canary"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]
    self.assertEqual(
        BrowserConfig.parse("android:chromium"),
        BrowserConfig(
            pth.AnyPosixPath("org.chromium.chrome"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

  @unittest.skip("Non-path browser short names are not yet supported "
                 "in complex configs.")
  def test_parse_inline_hjson_android(self):
    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]
    config_dict: JsonDict = {
        "browser": "com.android.chrome",
        "driver": "android",
    }
    self.assertEqual(
        BrowserConfig.parse(config_dict),
        BrowserConfig(
            pth.AnyPath("com.android.chrome"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

  def test_parse_invalid_android_package(self):
    self.platform.sh_results = [ADB_DEVICES_SINGLE_OUTPUT]
    with self.assertRaises(argparse.ArgumentTypeError):
      BrowserConfig.parse("")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse("adb:com.Foo .bar. com")
    self.assertIn("com.Foo .bar. com", str(cm.exception))

  def test_parse_fail_android_browser_string_not_dict(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse({"browser": "adb:chrome"})
    self.assertIn("browser", str(cm.exception))
    self.assertIn("short-form", str(cm.exception))

  @unittest.skipIf(plt.PLATFORM.is_win,
                   "Chrome downloading not supported on windows.")
  def test_parse_chrome_version(self):
    self.assertEqual(
        BrowserConfig.parse("applescript:chrome-m100"),
        BrowserConfig("chrome-m100",
                      DriverConfig(BrowserDriverType.APPLE_SCRIPT)))
    self.assertEqual(
        BrowserConfig.parse("selenium:chrome-116.0.5845.4"),
        BrowserConfig("chrome-116.0.5845.4",
                      DriverConfig(BrowserDriverType.WEB_DRIVER)))

  def test_parse_invalid_chrome_version(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = BrowserConfig.parse("applescript:chrome-m1")
    self.assertIn("m1", str(cm.exception))
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = BrowserConfig.parse("selenium:chrome-116.845.4.3.2.1.0")
    self.assertIn("116.845.4.3.2.1.0", str(cm.exception))

  def test_parse_adb_phone_serial(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT, ADB_DEVICES_OUTPUT]
    config = BrowserConfig.parse("0a388e93:chrome")
    assert isinstance(config, BrowserConfig)
    self.assertListEqual(self.platform.sh_results, [])
    self.assertEqual(len(self.platform.sh_cmds), 2)

    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    expected_driver = DriverConfig(
        BrowserDriverType.ANDROID, device_id="0a388e93")
    self.assertEqual(len(self.platform.sh_results), 0)
    self.assertEqual(len(self.platform.sh_cmds), 3)
    self.assertEqual(
        config,
        BrowserConfig(pth.AnyPosixPath("com.android.chrome"), expected_driver))

  @unittest.skipIf(plt.PLATFORM.is_macos, "Incompatible platform")
  def test_parse_adb_phone_serial_invalid_macos(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = BrowserConfig.parse("0XXXXXX:chrome")
    self.assertIn("0XXXXXX", str(cm.exception))
    self.assertEqual(len(self.platform.sh_cmds), 1)

  @unittest.skipIf(not plt.PLATFORM.is_macos, "Incompatible platform")
  def test_parse_adb_phone_serial_invalid_non_macos(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT, XCTRACE_DEVICES_OUTPUT]
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = BrowserConfig.parse("0XXXXXX:chrome")
    self.assertIn("0XXXXXX", str(cm.exception))
    self.assertEqual(len(self.platform.sh_cmds), 2)

  def test_parse_invalid_driver(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      BrowserConfig.parse("____:chrome")
    with self.assertRaises(argparse.ArgumentTypeError):
      # This has to be dealt with in users of DriverConfig.parse.
      BrowserConfig.parse("::chrome")

  def test_parse_invalid_hjson(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      BrowserConfig.parse("{:::}")
    with self.assertRaises(argparse.ArgumentTypeError):
      BrowserConfig.parse("{}")
    with self.assertRaises(argparse.ArgumentTypeError):
      BrowserConfig.parse("}")
    with self.assertRaises(argparse.ArgumentTypeError):
      BrowserConfig.parse("{path:something}")

  def test_parse_inline_hjson(self):
    config_dict: JsonDict = {"browser": "chrome", "driver": {"type": 'adb',}}

    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    with self.assertRaises(MultiException) as cm:
      _ = BrowserConfig.parse(hjson.dumps(config_dict))
    self.assertIn("devices", str(cm.exception))

    self.platform.sh_results = [ADB_DEVICES_SINGLE_OUTPUT]
    config_1 = BrowserConfig.parse(hjson.dumps(config_dict))
    assert isinstance(config_1, BrowserConfig)
    self.assertEqual(config_1.driver.type, BrowserDriverType.ANDROID)

    self.platform.sh_results = [ADB_DEVICES_SINGLE_OUTPUT]
    config_2 = BrowserConfig.parse_dict(config_dict)
    assert isinstance(config_2, BrowserConfig)
    self.assertEqual(config_2.driver.type, BrowserDriverType.ANDROID)
    self.assertEqual(config_1, config_2)

    short_config_dict: JsonDict = {
        "browser": "chrome",
        "driver": 'adb',
    }
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    with self.assertRaises(MultiException) as cm:
      _ = BrowserConfig.parse(hjson.dumps(short_config_dict))
    self.assertIn("devices", str(cm.exception))

    self.platform.sh_results = [ADB_DEVICES_SINGLE_OUTPUT]
    config_3 = BrowserConfig.parse_dict(short_config_dict)
    assert isinstance(config_3, BrowserConfig)
    self.assertEqual(config_3.driver.type, BrowserDriverType.ANDROID)
    self.assertEqual(config_1, config_3)

  def test_parse_inline_hjson_short_string(self):
    # We cannot easily configure the driver property from within the browser
    # config property.
    config_dict: JsonDict = {
        "browser": "adb:chrome",
    }
    with self.assertRaises(argparse.ArgumentTypeError):
      BrowserConfig.parse_dict(config_dict)

  def test_parse_inline_driver_browser(self):
    driver_path = pth.LocalPath("custom/chromedriver")
    config_dict: JsonDict = {
        "browser": "chrome",
        "driver": str(driver_path),
    }
    with self.assertRaises(ValueError):
      BrowserConfig.parse(hjson.dumps(config_dict))
    self.fs.create_file(driver_path, st_size=100)
    config = BrowserConfig.parse(hjson.dumps(config_dict))
    assert isinstance(config, BrowserConfig)
    self.assertEqual(config.browser,
                     mock_browser.MockChromeStable.mock_app_path())
    self.assertEqual(config.driver.type, BrowserDriverType.WEB_DRIVER)
    self.assertEqual(config.driver.path, driver_path)

  def test_parse_with_range_simple(self):
    versions = BrowserConfig.parse_with_range("chrome-m100")
    self.assertTupleEqual(versions, (BrowserConfig.parse("chrome-m100"),))

  def test_parse_with_range(self):
    result = (BrowserConfig.parse("chrome-m99"),
              BrowserConfig.parse("chrome-m100"),
              BrowserConfig.parse("chrome-m101"),
              BrowserConfig.parse("chrome-m102"))
    versions = BrowserConfig.parse_with_range("chrome-m99...chrome-m102")
    self.assertTupleEqual(versions, result)
    versions = BrowserConfig.parse_with_range("chrome-m99...m102")
    self.assertTupleEqual(versions, result)
    versions = BrowserConfig.parse_with_range("chrome-m99...102")
    self.assertTupleEqual(versions, result)

  def test_parse_with_range_invalid_empty(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse_with_range("")
    self.assertIn("empty", str(cm.exception))

  def test_parse_with_range_invalid_prefix(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse_with_range("chr-m100...chrome-m200")
    msg = str(cm.exception)
    self.assertIn("'chr-m'", msg)
    self.assertIn("'chrome-m'", msg)

  def test_parse_with_range_invalid_limit(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse_with_range("chr-m100...chr-m90")
    msg = str(cm.exception).lower()
    self.assertIn("larger", msg)
    self.assertIn("chr-m100...chr-m90", msg)

  def test_parse_with_range_missing_digits(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse_with_range("chr-m...chrome-m90")
    msg = str(cm.exception).lower()
    self.assertIn("start", msg)
    self.assertIn("'chr-m'", msg)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse_with_range("chr-m100...chr")
    msg = str(cm.exception).lower()
    self.assertIn("limit", msg)
    self.assertIn("'chr'", msg)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
