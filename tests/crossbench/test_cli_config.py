# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import copy
import pathlib
import unittest
from typing import Dict, Tuple, Type
from unittest import mock

import hjson
from frozendict import frozendict

from crossbench import plt
from crossbench.browsers.chrome.chrome import Chrome
from crossbench.browsers.chrome.webdriver import ChromeWebDriver
from crossbench.browsers.safari.safari import Safari
from crossbench.cli.config.base import ConfigError
from crossbench.cli.config.browser import BrowserConfig
from crossbench.cli.config.browser_variants import (BrowserVariantsConfig,
                                                    FlagGroupConfig)
from crossbench.cli.config.driver import (AmbiguousDriverIdentifier,
                                          BrowserDriverType, DriverConfig)
from crossbench.cli.config.network import (NetworkConfig, NetworkSpeedConfig,
                                           NetworkSpeedPreset, NetworkType)
from crossbench.cli.config.probe import ProbeConfig, ProbeListConfig
from crossbench.exception import MultiException
from crossbench.probes.power_sampler import PowerSamplerProbe
from crossbench.probes.v8.log import V8LogProbe
from crossbench.types import JsonDict
from tests import test_helper
from tests.crossbench import mock_browser
from tests.crossbench.mock_helper import (BaseCrossbenchTestCase,
                                          CrossbenchFakeFsTestCase)

ADB_DEVICES_SINGLE_OUTPUT = """List of devices attached
emulator-5556 device product:sdk_google_phone_x86_64 model:Android_SDK_built_for_x86_64 device:generic_x86_64"""

ADB_DEVICES_OUTPUT = f"""{ADB_DEVICES_SINGLE_OUTPUT}
emulator-5554 device product:sdk_google_phone_x86 model:Android_SDK_built_for_x86 device:generic_x86
0a388e93      device usb:1-1 product:razor model:Nexus_7 device:flo"""

XCTRACE_DEVICES_SINGLE_OUTPUT = """
== Devices ==
a-macbookpro3 (00001234-AAAA-BBBB-0000-11AA22BB33DD)
An iPhone (17.1.2) (00001111-11AA22BB33DD)

== Devices Offline ==
An iPhone Pro (17.1.1) (00002222-11AA22BB33DD)

== Simulators ==
iPad (10th generation) (17.0.1) (00001234-AAAA-BBBB-1111-11AA22BB33DD)
iPad (9th generation) Simulator (15.5) (00001234-AAAA-BBBB-2222-11AA22BB33DD
"""

XCTRACE_DEVICES_OUTPUT = """
== Devices ==
a-macbookpro3 (00001234-AAAA-BBBB-0000-11AA22BB33DD)
An iPhone (17.1.2) (00001111-11AA22BB33DD)
An iPhone Pro (17.1.1) (00002222-11AA22BB33DD)

== Devices Offline ==
An iPhone Pro Max (17.1.0) (00003333-11AA22BB33DD)

== Simulators ==
iPad (10th generation) (17.0.1) (00001234-AAAA-BBBB-1111-11AA22BB33DD)
iPad (9th generation) Simulator (15.5) (00001234-AAAA-BBBB-2222-11AA22BB33DD
"""


class BaseConfigTestCase(BaseCrossbenchTestCase):

  def setUp(self) -> None:
    super().setUp()
    adb_patcher = mock.patch(
        "crossbench.plt.android_adb._find_adb_bin",
        return_value=pathlib.Path("adb"))
    adb_patcher.start()
    self.addCleanup(adb_patcher.stop)


class DriverConfigTestCase(BaseConfigTestCase):

  def test_parse_invalid(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = DriverConfig.parse("")
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = DriverConfig.parse(":")
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = DriverConfig.parse("{:}")
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = DriverConfig.parse("}")
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = DriverConfig.parse("{")

  def test_parse_path(self):
    driver_path = self.out_dir / "driver"
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = DriverConfig.parse(str(driver_path))
    self.assertIn(str(driver_path), str(cm.exception))

    self.fs.create_file(driver_path)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = DriverConfig.parse(str(driver_path))
    message = str(cm.exception)
    self.assertIn(str(driver_path), message)
    self.assertIn("empty", message)

  def test_parse_inline_json(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    config_dict = {"type": 'adb', "settings": {"serial": "0a388e93"}}
    config = DriverConfig.parse(hjson.dumps(config_dict))
    assert isinstance(config, DriverConfig)
    self.assertEqual(config.type, BrowserDriverType.ANDROID)
    self.assertEqual(config.settings["serial"], "0a388e93")

    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    config = DriverConfig.load_dict(config_dict)
    assert isinstance(config, DriverConfig)
    self.assertEqual(config.type, BrowserDriverType.ANDROID)
    self.assertEqual(config.settings["serial"], "0a388e93")

  def test_parse_adb_phone_identifier_unknown(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    if self.platform.is_macos:
      self.platform.sh_results.append(XCTRACE_DEVICES_SINGLE_OUTPUT)

    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = DriverConfig.parse("Unknown Device X")
    self.assertIn("Unknown Device X", str(cm.exception))

  def test_parse_adb_phone_identifier_multiple(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    with self.assertRaises(AmbiguousDriverIdentifier) as cm:
      _ = DriverConfig.parse("emulator.*")
    message: str = str(cm.exception)
    self.assertIn("emulator-5554", message)
    self.assertIn("emulator-5556", message)
    self.assertEqual(len(self.platform.sh_cmds), 1)

  def test_parse_adb_phone_identifier(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT, ADB_DEVICES_OUTPUT]

    config = DriverConfig.parse("Nexus_7")
    assert isinstance(config, DriverConfig)
    self.assertEqual(len(self.platform.sh_cmds), 2)

    self.assertEqual(config.type, BrowserDriverType.ANDROID)
    self.assertEqual(config.settings["serial"], "0a388e93")

  def test_parse_adb_phone_serial(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT, ADB_DEVICES_OUTPUT]

    config = DriverConfig.parse("0a388e93")
    assert isinstance(config, DriverConfig)
    self.assertEqual(len(self.platform.sh_cmds), 2)

    self.assertEqual(config.type, BrowserDriverType.ANDROID)
    self.assertEqual(config.settings["serial"], "0a388e93")

  @unittest.skipIf(not plt.PLATFORM.is_macos, "Incompatible platform")
  def test_parse_ios_phone_serial(self):
    self.platform.sh_results = [
        ADB_DEVICES_OUTPUT, XCTRACE_DEVICES_SINGLE_OUTPUT,
        XCTRACE_DEVICES_SINGLE_OUTPUT
    ]

    config = DriverConfig.parse("00001111-11AA22BB33DD")
    assert isinstance(config, DriverConfig)
    self.assertEqual(len(self.platform.sh_cmds), 3)

    self.assertEqual(config.type, BrowserDriverType.IOS)
    self.assertEqual(config.settings["uuid"], "00001111-11AA22BB33DD")


class BrowserConfigTestCase(BaseConfigTestCase):

  def test_equal(self):
    path = Chrome.stable_path()
    self.assertEqual(
        BrowserConfig(path, DriverConfig(BrowserDriverType.default())),
        BrowserConfig(path, DriverConfig(BrowserDriverType.default())))
    self.assertNotEqual(
        BrowserConfig(path, DriverConfig(BrowserDriverType.default())),
        BrowserConfig(
            path,
            DriverConfig(
                BrowserDriverType.default(), settings=frozendict(custom=1))))
    self.assertNotEqual(
        BrowserConfig(path, DriverConfig(BrowserDriverType.default())),
        BrowserConfig(
            pathlib.Path("foo"), DriverConfig(BrowserDriverType.default())))

  def test_hashable(self):
    _ = hash(BrowserConfig.default())
    _ = hash(
        BrowserConfig(
            pathlib.Path("foo"),
            DriverConfig(
                BrowserDriverType.default(), settings=frozendict(custom=1))))

  def test_parse_name_or_path(self):
    path = Chrome.stable_path()
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
    path = pathlib.Path("foo/bar")
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
    self.assertIn("selenium\\bar", str(cm.exception))
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserConfig.parse("C:\\selenium\\bar")
    self.assertIn("C:\\selenium\\bar", str(cm.exception))

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
        BrowserConfig(Chrome.stable_path(),
                      DriverConfig(BrowserDriverType.WEB_DRIVER)))
    self.assertEqual(
        BrowserConfig.parse("webdriver:chrome"),
        BrowserConfig(Chrome.stable_path(),
                      DriverConfig(BrowserDriverType.WEB_DRIVER),
                      NetworkConfig.default()))
    self.assertEqual(
        BrowserConfig.parse("applescript:chrome"),
        BrowserConfig(Chrome.stable_path(),
                      DriverConfig(BrowserDriverType.APPLE_SCRIPT)))
    self.assertEqual(
        BrowserConfig.parse("osa:chrome"),
        BrowserConfig(Chrome.stable_path(),
                      DriverConfig(BrowserDriverType.APPLE_SCRIPT)))

  def test_parse_simple_with_driver_with_network(self):
    self.assertEqual(
        BrowserConfig.parse("chrome:4G"),
        BrowserConfig(Chrome.stable_path(),
                      DriverConfig(BrowserDriverType.WEB_DRIVER),
                      NetworkConfig.load_preset(NetworkSpeedPreset.MOBILE_4G)))
    self.assertEqual(
        BrowserConfig.parse("selenium:chrome:4G"),
        BrowserConfig(Chrome.stable_path(),
                      DriverConfig(BrowserDriverType.WEB_DRIVER),
                      NetworkConfig.load_preset(NetworkSpeedPreset.MOBILE_4G)))

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
        BrowserConfig(Chrome.stable_path(),
                      DriverConfig(BrowserDriverType.IOS)))
    self.assertEqual(config.network, NetworkConfig.default())

  def test_parse_simple_with_driver_ios_with_network(self):
    self.platform.sh_results = [
        XCTRACE_DEVICES_SINGLE_OUTPUT, XCTRACE_DEVICES_SINGLE_OUTPUT
    ]
    config = BrowserConfig.parse("ios:chrome:4G")
    self.assertEqual(
        config,
        BrowserConfig(Chrome.stable_path(), DriverConfig(BrowserDriverType.IOS),
                      NetworkConfig.load_preset(NetworkSpeedPreset.MOBILE_4G)))
    self.assertEqual(config.network,
                     NetworkConfig.load_preset(NetworkSpeedPreset.MOBILE_4G))

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
            pathlib.Path("com.android.chrome"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]
    self.assertEqual(
        BrowserConfig.parse("android:chrome-beta"),
        BrowserConfig(
            pathlib.Path("com.chrome.beta"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]
    self.assertEqual(
        BrowserConfig.parse("adb:chrome-dev"),
        BrowserConfig(
            pathlib.Path("com.chrome.dev"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]
    self.assertEqual(
        BrowserConfig.parse("android:chrome-canary"),
        BrowserConfig(
            pathlib.Path("com.chrome.canary"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]
    self.assertEqual(
        BrowserConfig.parse("android:chromium"),
        BrowserConfig(
            pathlib.Path("org.chromium.chrome"),
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
            pathlib.Path("com.android.chrome"),
            DriverConfig(BrowserDriverType.ANDROID)))
    self.assertListEqual(self.platform.sh_results, [])

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
      _ = BrowserConfig.parse("selenium:chrome-116.845.4")
    self.assertIn("116.845.4", str(cm.exception))

  def test_parse_adb_phone_serial(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT, ADB_DEVICES_OUTPUT]
    config = BrowserConfig.parse("0a388e93:chrome")
    assert isinstance(config, BrowserConfig)
    self.assertListEqual(self.platform.sh_results, [])
    self.assertEqual(len(self.platform.sh_cmds), 2)

    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    expected_driver = DriverConfig(
        BrowserDriverType.ANDROID, settings=frozendict(serial="0a388e93"))
    self.assertEqual(len(self.platform.sh_results), 0)
    self.assertEqual(len(self.platform.sh_cmds), 3)
    self.assertEqual(
        config,
        BrowserConfig(pathlib.Path("com.android.chrome"), expected_driver))

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
    config_dict: JsonDict = {
        "browser": "chrome",
        "driver": {
            "type": 'adb',
            "settings": {}
        }
    }

    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    with self.assertRaises(MultiException) as cm:
      _ = BrowserConfig.parse(hjson.dumps(config_dict))
    self.assertIn("devices", str(cm.exception))

    self.platform.sh_results = [ADB_DEVICES_SINGLE_OUTPUT]
    config = BrowserConfig.parse(hjson.dumps(config_dict))
    assert isinstance(config, BrowserConfig)
    self.assertEqual(config.driver.type, BrowserDriverType.ANDROID)

    self.platform.sh_results = [ADB_DEVICES_SINGLE_OUTPUT]
    config = BrowserConfig.load_dict(config_dict)
    assert isinstance(config, BrowserConfig)
    self.assertEqual(config.driver.type, BrowserDriverType.ANDROID)

  def test_parse_inline_driver_browser(self):
    driver_path = pathlib.Path("custom/chromedriver")
    config_dict: JsonDict = {
        "browser": "chrome",
        "driver": str(driver_path),
    }
    with self.assertRaises(ValueError):
      BrowserConfig.parse(hjson.dumps(config_dict))
    self.fs.create_file(driver_path, st_size=100)
    config = BrowserConfig.parse(hjson.dumps(config_dict))
    assert isinstance(config, BrowserConfig)
    self.assertEqual(config.browser, mock_browser.MockChromeStable.APP_PATH)
    self.assertEqual(config.driver.type, BrowserDriverType.WEB_DRIVER)
    self.assertEqual(config.driver.path, driver_path)


class TestProbeConfig(CrossbenchFakeFsTestCase):
  # pylint: disable=expression-not-assigned

  def parse_config(self, config_data) -> ProbeListConfig:
    probe_config_file = pathlib.Path("/probe.config.hjson")
    with probe_config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)
    with probe_config_file.open(encoding="utf-8") as f:
      return ProbeListConfig.load(f)

  def test_invalid_empty(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      self.parse_config({}).probes
    with self.assertRaises(argparse.ArgumentTypeError):
      self.parse_config({"foo": {}}).probes

  def test_invalid_names(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      self.parse_config({"probes": {"invalid probe name": {}}}).probes

  def test_empty(self):
    config = self.parse_config({"probes": {}})
    self.assertListEqual(config.probes, [])

  def test_single_v8_log(self):
    js_flags = ["--log-maps", "--log-function-events"]
    config = self.parse_config(
        {"probes": {
            "v8.log": {
                "prof": True,
                "js_flags": js_flags,
            }
        }})
    self.assertTrue(len(config.probes), 1)
    probe = config.probes[0]
    assert isinstance(probe, V8LogProbe)
    for flag in js_flags + ["--log-all"]:
      self.assertIn(flag, probe.js_flags)

  def test_from_cli_args(self):
    file = pathlib.Path("probe.config.hjson")
    js_flags = ["--log-maps", "--log-function-events"]
    config_data: JsonDict = {
        "probes": {
            "v8.log": {
                "prof": True,
                "js_flags": js_flags,
            }
        }
    }
    with file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)
    args = mock.Mock(probe_config=file)
    config = ProbeListConfig.from_cli_args(args)
    self.assertTrue(len(config.probes), 1)
    probe = config.probes[0]
    assert isinstance(probe, V8LogProbe)
    for flag in js_flags + ["--log-all"]:
      self.assertIn(flag, probe.js_flags)

  def test_inline_config(self):
    mock_d8_file = pathlib.Path("out/d8")
    self.fs.create_file(mock_d8_file, st_size=8 * 1024)
    config_data = {"d8_binary": str(mock_d8_file)}
    args = mock.Mock(probe_config=None, throw=True, wraps=False)

    args.probe = [
        ProbeConfig.parse(f"v8.log{hjson.dumps(config_data)}"),
    ]
    config = ProbeListConfig.from_cli_args(args)
    self.assertTrue(len(config.probes), 1)
    probe = config.probes[0]
    self.assertTrue(isinstance(probe, V8LogProbe))

    args.probe = [
        ProbeConfig.parse(f"v8.log:{hjson.dumps(config_data)}"),
    ]
    config = ProbeListConfig.from_cli_args(args)
    self.assertTrue(len(config.probes), 1)
    probe = config.probes[0]
    self.assertTrue(isinstance(probe, V8LogProbe))

  def test_inline_config_invalid(self):
    mock_d8_file = pathlib.Path("out/d8")
    self.fs.create_file(mock_d8_file)
    config_data = {"d8_binary": str(mock_d8_file)}
    trailing_brace = "}"
    with self.assertRaises(argparse.ArgumentTypeError):
      ProbeConfig.parse(f"v8.log{hjson.dumps(config_data)}{trailing_brace}")
    with self.assertRaises(argparse.ArgumentTypeError):
      ProbeConfig.parse(f"v8.log:{hjson.dumps(config_data)}{trailing_brace}")
    with self.assertRaises(argparse.ArgumentTypeError):
      ProbeConfig.parse("v8.log::")

  def test_inline_config_dir_instead_of_file(self):
    mock_dir = pathlib.Path("some/dir")
    mock_dir.mkdir(parents=True)
    config_data = {"d8_binary": str(mock_dir)}
    args = mock.Mock(
        probe=[ProbeConfig.parse(f"v8.log{hjson.dumps(config_data)}")],
        probe_config=None,
        throw=True,
        wraps=False)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      ProbeListConfig.from_cli_args(args)
    self.assertIn(str(mock_dir), str(cm.exception))

  def test_inline_config_non_existent_file(self):
    config_data = {"d8_binary": "does/not/exist/d8"}
    args = mock.Mock(
        probe=[ProbeConfig.parse(f"v8.log{hjson.dumps(config_data)}")],
        probe_config=None,
        throw=True,
        wraps=False)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      ProbeListConfig.from_cli_args(args)
    expected_path = pathlib.Path("does/not/exist/d8")
    self.assertIn(str(expected_path), str(cm.exception))

  def test_multiple_probes(self):
    powersampler_bin = pathlib.Path("/powersampler.bin")
    powersampler_bin.touch()
    config = self.parse_config({
        "probes": {
            "v8.log": {
                "log_all": True,
            },
            "powersampler": {
                "bin_path": str(powersampler_bin)
            }
        }
    })
    self.assertTrue(len(config.probes), 2)
    log_probe = config.probes[0]
    assert isinstance(log_probe, V8LogProbe)
    powersampler_probe = config.probes[1]
    assert isinstance(powersampler_probe, PowerSamplerProbe)
    self.assertEqual(powersampler_probe.bin_path, powersampler_bin)


class TestBrowserVariantsConfig(BaseConfigTestCase):
  # pylint: disable=expression-not-assigned

  EXAMPLE_CONFIG_PATH = (
      test_helper.config_dir() / "browser.config.example.hjson")

  def setUp(self):
    super().setUp()
    self.browser_lookup: Dict[str, Tuple[
        Type[mock_browser.MockBrowser], BrowserConfig]] = {
            "chr-stable":
                (mock_browser.MockChromeStable,
                 BrowserConfig(mock_browser.MockChromeStable.APP_PATH)),
            "chr-dev": (mock_browser.MockChromeDev,
                        BrowserConfig(mock_browser.MockChromeDev.APP_PATH)),
            "chrome-stable":
                (mock_browser.MockChromeStable,
                 BrowserConfig(mock_browser.MockChromeStable.APP_PATH)),
            "chrome-dev": (mock_browser.MockChromeDev,
                           BrowserConfig(mock_browser.MockChromeDev.APP_PATH)),
        }
    for _, (_, browser_config) in self.browser_lookup.items():
      self.assertTrue(browser_config.path.exists())

  @unittest.skipIf(hjson.__name__ != "hjson", "hjson not available")
  def test_load_browser_config_template(self):
    if not self.EXAMPLE_CONFIG_PATH.exists():
      raise unittest.SkipTest(
          f"Test file {self.EXAMPLE_CONFIG_PATH} does not exist")
    self.fs.add_real_file(self.EXAMPLE_CONFIG_PATH)
    with self.EXAMPLE_CONFIG_PATH.open(encoding="utf-8") as f:
      config = BrowserVariantsConfig(
          browser_lookup_override=self.browser_lookup)
      config.load(f, args=self.mock_args)
    self.assertIn("flag-group-1", config.flag_groups)
    self.assertGreaterEqual(len(config.flag_groups), 1)
    self.assertGreaterEqual(len(config.variants), 1)

  def test_browser_labels_attributes(self):
    browsers = BrowserVariantsConfig(
        {
            "browsers": {
                "chrome-stable-default": {
                    "path": "chrome-stable",
                },
                "chrome-stable-noopt": {
                    "path": "chrome-stable",
                    "flags": ["--js-flags=--max-opt=0",]
                },
                "chrome-stable-custom": {
                    "label": "custom-label-property",
                    "path": "chrome-stable",
                    "flags": ["--js-flags=--max-opt=0",]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args).variants
    self.assertEqual(len(browsers), 3)
    self.assertEqual(browsers[0].label, "chrome-stable-default")
    self.assertEqual(browsers[1].label, "chrome-stable-noopt")
    self.assertEqual(browsers[2].label, "custom-label-property")

  def test_browser_label_args(self):
    self.platform.sh_results = [ADB_DEVICES_SINGLE_OUTPUT]
    args = self.mock_args
    adb_config = BrowserConfig.parse("adb:chrome")
    desktop_config = BrowserConfig.parse("chrome")
    args.browser = [
        adb_config,
        desktop_config,
    ]
    self.assertFalse(self.platform.sh_results)
    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT,
        ADB_DEVICES_SINGLE_OUTPUT,
    ]

    def mock_get_browser_cls(browser_config: BrowserConfig):
      if browser_config is adb_config:
        return mock_browser.MockChromeAndroidStable
      if browser_config is desktop_config:
        return mock_browser.MockChromeStable
      raise ValueError("Unknown browser_config")

    with mock.patch.object(
        BrowserVariantsConfig,
        "_get_browser_cls",
        side_effect=mock_get_browser_cls), mock.patch(
            "crossbench.plt.AndroidAdbPlatform.machine",
            new_callable=mock.PropertyMock,
            return_value=plt.MachineArch.ARM_64):
      browsers = BrowserVariantsConfig.from_cli_args(args).variants
    self.assertEqual(len(browsers), 2)
    self.assertEqual(browsers[0].label, "android.arm64.remote_0")
    self.assertEqual(browsers[1].label, "mock.arm64.local_1")

    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "browsers": {
                  "chrome-stable-label": {
                      "path": "chrome-stable",
                  },
                  "chrome-stable-custom": {
                      "label": "chrome-stable-label",
                      "path": "chrome-stable",
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    message = str(cm.exception)
    self.assertIn("chrome-stable-label", message)
    self.assertIn("chrome-stable-custom", message)

  def test_flag_combination_invalid(self):
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {
                      "invalid-flag-name": [None, "", "v1"],
                  },
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": ["group1",]
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    message = str(cm.exception)
    self.assertIn("group1", message)
    self.assertIn("invalid-flag-name", message)

  def test_flag_combination_none(self):
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {
                      "--foo": ["None,", "", "v1"],
                  },
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": ["group1"]
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    self.assertIn("None", str(cm.exception))

  def test_flag_combination_duplicate(self):
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {
                      "--duplicate-flag": [None, "", "v1"],
                  },
                  "group2": {
                      "--duplicate-flag": [None, "", "v1"],
                  }
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": ["group1", "group2"]
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    self.assertIn("--duplicate-flag", str(cm.exception))

  def test_empty(self):
    with self.assertRaises(ConfigError):
      BrowserVariantsConfig({"other": {}}, args=self.mock_args).variants
    with self.assertRaises(ConfigError):
      BrowserVariantsConfig({"browsers": {}}, args=self.mock_args).variants

  def test_unknown_group(self):
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": ["unknown-flag-group"]
                  }
              }
          },
          args=self.mock_args).variants
    self.assertIn("unknown-flag-group", str(cm.exception))

  def test_duplicate_group(self):
    with self.assertRaises(ConfigError):
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {}
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": ["group1", "group1"]
                  }
              }
          },
          args=self.mock_args).variants

  def test_non_list_group(self):
    BrowserVariantsConfig(
        {
            "flags": {
                "group1": {}
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": "group1"
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args).variants
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {}
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": 1
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    self.assertIn("chrome-stable", str(cm.exception))
    self.assertIn("flags", str(cm.exception))

    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {}
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": {
                          "group1": True
                      }
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    self.assertIn("chrome-stable", str(cm.exception))
    self.assertIn("flags", str(cm.exception))

  def test_duplicate_flag_variant_value(self):
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {
                      "--flag": ["repeated", "repeated"]
                  }
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": "group1",
                  }
              }
          },
          args=self.mock_args).variants
    self.assertIn("group1", str(cm.exception))
    self.assertIn("--flag", str(cm.exception))

  def test_unknown_path(self):
    with self.assertRaises(Exception):
      BrowserVariantsConfig(
          {
              "browsers": {
                  "chrome-stable": {
                      "path": "path/does/not/exist",
                  }
              }
          },
          args=self.mock_args).variants
    with self.assertRaises(Exception):
      BrowserVariantsConfig(
          {
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-unknown",
                  }
              }
          },
          args=self.mock_args).variants

  def test_flag_combination_simple(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "group1": {
                    "--foo": [None, "", "v1"],
                }
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": ["group1"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    browsers = config.variants
    self.assertEqual(len(browsers), 3)
    for browser in browsers:
      assert isinstance(browser, mock_browser.MockChromeStable)
      self.assertDictEqual(dict(browser.js_flags), {})
    self.assertDictEqual(dict(browsers[0].flags), {})
    self.assertDictEqual(dict(browsers[1].flags), {"--foo": None})
    self.assertDictEqual(dict(browsers[2].flags), {"--foo": "v1"})

  def test_flag_combination(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "group1": {
                    "--foo": [None, "", "v1"],
                    "--bar": [None, "", "v1"],
                }
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": ["group1"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    self.assertEqual(len(config.variants), 3 * 3)

  def test_flag_combination_mixed_inline(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "compile-hints-experiment": {
                    "--enable-features": [None, "ConsumeCompileHints"]
                }
            },
            "browsers": {
                "chrome-release": {
                    "path": "chrome-stable",
                    "flags": ["--no-sandbox", "compile-hints-experiment"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    browsers = config.variants
    self.assertEqual(len(browsers), 2)
    self.assertListEqual(["--no-sandbox"], list(browsers[0].flags.get_list()))
    self.assertListEqual(
        ["--no-sandbox", "--enable-features=ConsumeCompileHints"],
        list(browsers[1].flags.get_list()))

  def test_flag_single_inline(self):
    config = BrowserVariantsConfig(
        {
            "browsers": {
                "chrome-release": {
                    "path": "chrome-stable",
                    "flags": "--no-sandbox",
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    browsers = config.variants
    self.assertEqual(len(browsers), 1)
    self.assertListEqual(["--no-sandbox"], list(browsers[0].flags.get_list()))

  def test_flag_combination_mixed_fixed(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "compile-hints-experiment": {
                    "--no-sandbox": "",
                    "--enable-features": [None, "ConsumeCompileHints"]
                }
            },
            "browsers": {
                "chrome-release": {
                    "path": "chrome-stable",
                    "flags": "compile-hints-experiment"
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    browsers = config.variants
    self.assertEqual(len(browsers), 2)
    self.assertListEqual(["--no-sandbox"], list(browsers[0].flags.get_list()))
    self.assertListEqual(
        ["--no-sandbox", "--enable-features=ConsumeCompileHints"],
        list(browsers[1].flags.get_list()))

  def test_no_flags(self):
    config = BrowserVariantsConfig(
        {
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                },
                "chrome-dev": {
                    "path": "chrome-dev",
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    self.assertEqual(len(config.variants), 2)
    browser_0 = config.variants[0]
    assert isinstance(browser_0, mock_browser.MockChromeStable)
    self.assertEqual(browser_0.app_path, mock_browser.MockChromeStable.APP_PATH)
    browser_1 = config.variants[1]
    assert isinstance(browser_1, mock_browser.MockChromeDev)
    self.assertEqual(browser_1.app_path, mock_browser.MockChromeDev.APP_PATH)

  def test_custom_driver(self):
    chromedriver = pathlib.Path("path/to/chromedriver")
    variants_config = {
        "browsers": {
            "chrome-stable": {
                "browser": "chrome-stable",
                "driver": str(chromedriver),
            }
        }
    }
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserVariantsConfig(
          copy.deepcopy(variants_config),
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args)
    self.assertIn(str(chromedriver), str(cm.exception))

    self.fs.create_file(chromedriver, st_size=100)
    with mock.patch.object(
        BrowserVariantsConfig,
        "_get_browser_cls",
        return_value=mock_browser.MockChromeStable):
      config = BrowserVariantsConfig(
          variants_config,
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args)
    self.assertFalse(variants_config["browsers"]["chrome-stable"])
    self.assertEqual(len(config.variants), 1)
    browser_0 = config.variants[0]
    assert isinstance(browser_0, mock_browser.MockChromeStable)
    self.assertEqual(browser_0.app_path, mock_browser.MockChromeStable.APP_PATH)

  def test_inline_flags(self):
    with mock.patch.object(
        ChromeWebDriver, "_extract_version",
        return_value="101.22.333.44"), mock.patch.object(
            Chrome,
            "stable_path",
            return_value=mock_browser.MockChromeStable.APP_PATH):

      config = BrowserVariantsConfig(
          {
              "browsers": {
                  "stable": {
                      "path": "chrome-stable",
                      "flags": ["--foo=bar"]
                  }
              }
          },
          args=self.mock_args)
      self.assertEqual(len(config.variants), 1)
      browser = config.variants[0]
      # TODO: Fix once app lookup is cleaned up
      self.assertEqual(browser.app_path, mock_browser.MockChromeStable.APP_PATH)
      self.assertEqual(browser.version, "101.22.333.44")

  def test_inline_load_safari(self):
    if not plt.PLATFORM.is_macos:
      return
    with mock.patch.object(Safari, "_extract_version", return_value="16.0"):
      config = BrowserVariantsConfig(
          {"browsers": {
              "safari": {
                  "path": "safari",
              }
          }}, args=self.mock_args)
      self.assertEqual(len(config.variants), 1)

  def test_flag_combination_with_fixed(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "group1": {
                    "--foo": [None, "", "v1"],
                    "--bar": [None, "", "v1"],
                    "--always_1": "true",
                    "--always_2": "true",
                    "--always_3": "true",
                }
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": ["group1"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    self.assertEqual(len(config.variants), 3 * 3)
    for browser in config.variants:
      assert isinstance(browser, mock_browser.MockChromeStable)
      self.assertEqual(browser.app_path, mock_browser.MockChromeStable.APP_PATH)

  def test_flag_group_combination(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "group1": {
                    "--foo": [None, "", "v1"],
                },
                "group2": {
                    "--bar": [None, "", "v1"],
                },
                "group3": {
                    "--other": ["v1", "v2"],
                }
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": ["group1", "group2", "group3"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    self.assertEqual(len(config.variants), 3 * 3 * 2)

  def test_from_cli_args_browser_config(self):
    if self.platform.is_win:
      self.skipTest("No auto-download available on windows")
    browser_cls = mock_browser.MockChromeStable
    # TODO: migrate to with_stem once python 3.9 is available everywhere
    suffix = browser_cls.APP_PATH.suffix
    browser_bin = browser_cls.APP_PATH.with_name(
        f"Custom Google Chrome{suffix}")
    browser_cls.setup_bin(self.fs, browser_bin, "Chrome")
    config_data = {"browsers": {"chrome-stable": {"path": str(browser_bin),}}}
    config_file = pathlib.Path("config.hjson")
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)

    args = mock.Mock(browser=None, browser_config=config_file, driver_path=None)
    with mock.patch.object(
        BrowserVariantsConfig, "_get_browser_cls", return_value=browser_cls):
      config = BrowserVariantsConfig.from_cli_args(args)
    self.assertEqual(len(config.variants), 1)
    browser = config.variants[0]
    self.assertIsInstance(browser, browser_cls)
    self.assertEqual(browser.app_path, browser_bin)

  def test_from_cli_args_browser(self):
    if self.platform.is_win:
      self.skipTest("No auto-download available on windows")
    browser_cls = mock_browser.MockChromeStable
    # TODO: migrate to with_stem once python 3.9 is available everywhere
    suffix = browser_cls.APP_PATH.suffix
    browser_bin = browser_cls.APP_PATH.with_name(
        f"Custom Google Chrome{suffix}")
    browser_cls.setup_bin(self.fs, browser_bin, "Chrome")
    args = mock.Mock(
        browser=[
            BrowserConfig(browser_bin),
        ],
        browser_config=None,
        enable_features=None,
        disable_features=None,
        driver_path=None,
        js_flags=None,
        other_browser_args=[])
    with mock.patch.object(
        BrowserVariantsConfig, "_get_browser_cls", return_value=browser_cls):
      config = BrowserVariantsConfig.from_cli_args(args)
    self.assertEqual(len(config.variants), 1)
    browser = config.variants[0]
    self.assertIsInstance(browser, browser_cls)
    self.assertEqual(browser.app_path, browser_bin)


class TestFlagGroupConfig(unittest.TestCase):

  def parse(self, config_dict):
    config = FlagGroupConfig("test", config_dict)
    variants = list(config.get_variant_items())
    return variants

  def test_empty(self):
    config = FlagGroupConfig("empty_name", {})
    self.assertEqual(config.name, "empty_name")
    variants = list(config.get_variant_items())
    self.assertEqual(len(variants), 0)

  def test_single_flag(self):
    variants = self.parse({"--foo": set()})
    self.assertListEqual(variants, [
        (),
    ])

    variants = self.parse({"--foo": []})
    self.assertListEqual(variants, [
        (),
    ])

    variants = self.parse({"--foo": (None,)})
    self.assertListEqual(variants, [
        (None,),
    ])

    variants = self.parse({"--foo": ("",)})
    self.assertEqual(len(variants), 1)
    self.assertTupleEqual(
        variants[0],
        (("--foo", None),),
    )

    variants = self.parse({"--foo": (
        "",
        None,
    )})
    self.assertEqual(len(variants), 1)
    self.assertTupleEqual(variants[0], (("--foo", None), None))

    variants = self.parse({"--foo": (
        "v1",
        "v2",
        "",
        None,
    )})
    self.assertEqual(len(variants), 1)
    self.assertTupleEqual(variants[0], (("--foo", "v1"), ("--foo", "v2"),
                                        ("--foo", None), None))

  def test_two_flags(self):
    variants = self.parse({"--foo": [], "--bar": []})
    self.assertListEqual(variants, [(), ()])

    variants = self.parse({"--foo": "a", "--bar": "b"})
    self.assertEqual(len(variants), 2)
    self.assertTupleEqual(variants[0], (("--foo", "a"),))
    self.assertTupleEqual(variants[1], (("--bar", "b"),))

    variants = self.parse({"--foo": ["a1", "a2"], "--bar": "b"})
    self.assertEqual(len(variants), 2)
    self.assertTupleEqual(variants[0], (
        ("--foo", "a1"),
        ("--foo", "a2"),
    ))
    self.assertTupleEqual(variants[1], (("--bar", "b"),))

    variants = self.parse({"--foo": ["a1", "a2"], "--bar": ["b1", "b2"]})
    self.assertEqual(len(variants), 2)
    self.assertTupleEqual(variants[0], (
        ("--foo", "a1"),
        ("--foo", "a2"),
    ))
    self.assertTupleEqual(variants[1], (
        ("--bar", "b1"),
        ("--bar", "b2"),
    ))


class NetworkSpeedConfigTestCase(BaseConfigTestCase):

  def test_parse_invalid(self):
    for invalid in ("", None, "---"):
      with self.assertRaises(argparse.ArgumentTypeError):
        NetworkSpeedConfig.parse(invalid)
      with self.assertRaises(argparse.ArgumentTypeError):
        NetworkSpeedConfig.loads(str(invalid))

  def test_parse_default(self):
    config = NetworkSpeedConfig.parse("default")
    self.assertEqual(config, NetworkSpeedConfig.default())

  def test_default(self):
    config = NetworkSpeedConfig.default()
    self.assertEqual(config.rtt_ms, None)
    self.assertEqual(config.in_kbps, None)
    self.assertEqual(config.out_kbps, None)
    self.assertEqual(config.window, None)

  def test_parse_speed_preset(self):
    config = NetworkSpeedConfig.parse("4G")
    self.assertNotEqual(config, NetworkSpeedConfig.default())

    for preset in NetworkSpeedPreset:  # pytype: disable=missing-parameter
      config = NetworkSpeedConfig.parse(str(preset))
      self.assertEqual(config, NetworkSpeedConfig.load_preset(preset))

  def test_parse_invalid_preset(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkSpeedConfig.parse("1xx4")
    self.assertIn("1xx4", str(cm.exception))
    self.assertIn("Choices are", str(cm.exception))


class NetworkConfigTestCase(BaseConfigTestCase):

  def test_parse_invalid(self):
    for invalid in ("", None, "---"):
      with self.assertRaises(argparse.ArgumentTypeError):
        NetworkConfig.parse(invalid)
      with self.assertRaises(argparse.ArgumentTypeError):
        NetworkConfig.loads(str(invalid))

  def test_parse_default(self):
    config = NetworkConfig.parse("default")
    self.assertEqual(config, NetworkConfig.default())

  def test_default(self):
    config = NetworkConfig.default()
    self.assertEqual(config.type, NetworkType.LIVE)
    self.assertEqual(config.speed, NetworkSpeedConfig.default())

  def test_parse_replay_archive_invalid(self):
    path = pathlib.Path("/foo/bar/wprgo.archive")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkConfig.parse(str(path))
    message = str(cm.exception)
    self.assertIn("wpr.go archive", message)
    self.assertIn("exist", message)

    self.fs.create_file(path)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkConfig.parse(str(path))
    message = str(cm.exception)
    self.assertIn("wpr.go archive", message)
    self.assertIn("empty", message)

  def test_parse_wprgo_archive(self):
    path = pathlib.Path("/foo/bar/wprgo.archive")
    self.fs.create_file(path, st_size=1024)
    config = NetworkConfig.parse(str(path))
    assert isinstance(config, NetworkConfig)
    self.assertEqual(config.type, NetworkType.WPR)
    self.assertEqual(config.path, path)
    self.assertEqual(config.speed, NetworkSpeedConfig.default())

  def test_invalid_constructor_params(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = NetworkConfig(path=pathlib.Path("foo/bar"))
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = NetworkConfig(type=NetworkType.LOCAL, path=None)
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = NetworkConfig(type=NetworkType.WPR, path=None)

  def test_parse_speed_preset(self):
    for preset in NetworkSpeedPreset:  # pytype: disable=missing-parameter
      config = NetworkConfig.loads(preset.value)
      self.assertEqual(config.speed, NetworkSpeedConfig.load_preset(preset))

  def test_parse_wpr_invalid(self):
    dir_path = pathlib.Path("test/dir")
    dir_path.mkdir(parents=True)
    for invalid in ("", "default", "4G", dir_path, str(dir_path)):
      with self.assertRaises(argparse.ArgumentTypeError):
        NetworkConfig.parse_wpr(invalid)

  def test_parse_wpr(self):
    archive_path = pathlib.Path("test/archive.wprgo")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkConfig.parse_wpr(archive_path)
    self.assertIn(str(archive_path), str(cm.exception))
    self.fs.create_file(archive_path, st_size=100)
    config = NetworkConfig.parse_wpr(archive_path)
    self.assertEqual(config.type, NetworkType.WPR)
    self.assertEqual(config.speed, NetworkSpeedConfig.default())
    self.assertEqual(config.path, archive_path)
    self.assertEqual(config, NetworkConfig.parse(archive_path))

  def test_parse_dict_default(self):
    config = NetworkConfig.parse({})
    self.assertEqual(config, NetworkConfig.default())

  def test_parse_dict_speed(self):
    config: NetworkConfig = NetworkConfig.parse({"speed": "4G"})
    self.assertNotEqual(config, NetworkConfig.default())
    self.assertEqual(config.type, NetworkType.LIVE)
    self.assertEqual(
        config.speed,
        NetworkSpeedConfig.load_preset(NetworkSpeedPreset.MOBILE_4G))
    self.assertIsNone(config.path)

  def test_parse_dict_wpr(self):
    archive_path = pathlib.Path("test/archive.wprgo")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkConfig.parse({"type": "wpr", "path": archive_path})
    self.assertIn(str(archive_path), str(cm.exception))
    self.fs.create_file(archive_path, st_size=100)
    config = NetworkConfig.parse({"type": "wpr", "path": archive_path})
    self.assertEqual(config, NetworkConfig.parse_wpr(archive_path))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
