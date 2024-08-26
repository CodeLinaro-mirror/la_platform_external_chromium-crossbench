# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import unittest

import hjson

from crossbench import plt
from crossbench.cli.config.driver import (AmbiguousDriverIdentifier,
                                          BrowserDriverType, DriverConfig)
from crossbench.exception import ArgumentTypeMultiException
from crossbench.plt.chromeos_ssh import ChromeOsSshPlatform
from tests import test_helper
from tests.crossbench.cli.config.base import (ADB_DEVICES_OUTPUT,
                                              XCTRACE_DEVICES_SINGLE_OUTPUT,
                                              BaseConfigTestCase)


class BrowserDriverTypeTestCase(unittest.TestCase):

  def test_default(self):
    self.assertEqual(BrowserDriverType.default(), BrowserDriverType.WEB_DRIVER)

  def test_parse_invalid(self):
    for invalid in ["invalid", None, [], (), {}]:
      with self.assertRaises(argparse.ArgumentTypeError):
        BrowserDriverType.parse(invalid)

  def test_parse_str(self):
    test_data = {
        "": BrowserDriverType.default(),
        "selenium": BrowserDriverType.WEB_DRIVER,
        "webdriver": BrowserDriverType.WEB_DRIVER,
        "applescript": BrowserDriverType.APPLE_SCRIPT,
        "osa": BrowserDriverType.APPLE_SCRIPT,
        "android": BrowserDriverType.ANDROID,
        "adb": BrowserDriverType.ANDROID,
        "iphone": BrowserDriverType.IOS,
        "ios": BrowserDriverType.IOS,
        "ssh": BrowserDriverType.LINUX_SSH,
        "chromeos-ssh": BrowserDriverType.CHROMEOS_SSH,
    }
    for value, result in test_data.items():
      self.assertEqual(BrowserDriverType.parse(value), result)

  def test_parse_enum(self):
    for driver_type in BrowserDriverType:
      self.assertEqual(BrowserDriverType.parse(driver_type), driver_type)


class DriverConfigTestCase(BaseConfigTestCase):

  def test_default(self):
    default = DriverConfig.default()
    self.assertEqual(default.type, BrowserDriverType.WEB_DRIVER)
    self.assertTrue(default.is_local)
    self.assertFalse(default.is_remote)

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

  def test_parse_driver_path_invalid(self):
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

  def test_parse_driver_path(self):
    chromedriver_path = self.out_dir / "chromedriver"
    self.fs.create_file(chromedriver_path, st_size=100)
    driver = DriverConfig.parse(str(chromedriver_path))
    self.assertEqual(driver.path, chromedriver_path)

    config = {"path": str(chromedriver_path)}
    driver_2 = DriverConfig.parse(config)
    self.assertEqual(driver_2.path, chromedriver_path)
    self.assertEqual(driver, driver_2)

  def test_parse_dict_device_id_conflict(self):
    self.platform.sh_results = []
    config_dict = {
        "type": 'adb',
        "device_id": "1234",
        "settings": {
            "device_id": "ABCD"
        }
    }
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      DriverConfig.parse(config_dict)
    self.assertIn("1234", str(cm.exception))
    self.assertIn("ABCD", str(cm.exception))

  def test_parse_dict_chromeos_ssh(self):
    config_dict = {
        "type": "chromeos-ssh",
        "settings": {
            "host": "chromeos6-row17-rack14-host7",
            "port": "9515",
            "ssh_port": "22",
            "ssh_user": "root"
        }
    }
    self.platform.expect_sh(
        "ssh", "-p", config_dict["settings"]["ssh_port"],
        f"{config_dict['settings']['ssh_user']}@{config_dict['settings']['host']}",
        f"'[' -e {ChromeOsSshPlatform.AUTOLOGIN_PATH} ']'")
    config = DriverConfig.parse(config_dict)
    assert isinstance(config, DriverConfig)
    self.assertEqual(config.type, BrowserDriverType.CHROMEOS_SSH)
    self.assertTrue(config.is_remote)
    self.assertFalse(config.is_local)
    platform = config.get_platform()
    assert isinstance(platform, ChromeOsSshPlatform)
    self.assertEqual(platform.host, "chromeos6-row17-rack14-host7")
    self.assertEqual(platform.port, 9515)
    self.assertEqual(platform._ssh_port, 22)
    self.assertEqual(platform._ssh_user, "root")

  def test_parse_inline_json_adb(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    config_dict = {"type": 'adb', "settings": {"device_id": "0a388e93"}}
    config_1 = DriverConfig.parse(hjson.dumps(config_dict))
    assert isinstance(config_1, DriverConfig)
    self.assertEqual(config_1.type, BrowserDriverType.ANDROID)
    self.assertEqual(config_1.device_id, "0a388e93")
    self.assertEqual(config_1.settings["device_id"], "0a388e93")
    self.assertTrue(config_1.is_remote)
    self.assertFalse(config_1.is_local)
    self.assertIsNone(config_1.adb_bin)

    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    config_2 = DriverConfig.parse_dict(config_dict)
    assert isinstance(config_2, DriverConfig)
    self.assertEqual(config_2.type, BrowserDriverType.ANDROID)
    self.assertEqual(config_2.device_id, "0a388e93")
    self.assertEqual(config_2.settings["device_id"], "0a388e93")
    self.assertTrue(config_2.is_remote)
    self.assertFalse(config_2.is_local)
    self.assertIsNone(config_2.adb_bin)
    self.assertEqual(config_1, config_2)

    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    config_dict = {"type": 'adb', "device_id": "0a388e93"}
    config_3 = DriverConfig.parse_dict(config_dict)
    assert isinstance(config_3, DriverConfig)
    self.assertEqual(config_3.type, BrowserDriverType.ANDROID)
    self.assertEqual(config_3.device_id, "0a388e93")
    self.assertTrue(config_3.is_remote)
    self.assertFalse(config_3.is_local)
    self.assertIsNone(config_3.settings)
    self.assertIsNone(config_2.adb_bin)
    self.assertNotEqual(config_1, config_3)
    self.assertNotEqual(config_2, config_3)

  def test_parse_custom_adb_bin(self):
    adb_bin = self.out_dir / "adb"
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    config_dict = {
        "type": "adb",
        "device_id": "0a388e93",
        "adb_bin": str(adb_bin)
    }
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = DriverConfig.parse(hjson.dumps(config_dict))
    self.assertIn(str(adb_bin), str(cm.exception))
    self.fs.create_file(adb_bin, st_size=100)
    config = DriverConfig.parse(hjson.dumps(config_dict))
    assert isinstance(config, DriverConfig)
    self.assertEqual(config.type, BrowserDriverType.ANDROID)
    self.assertEqual(config.adb_bin, adb_bin)

  def test_parse_adb_phone_identifier_unknown(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    if self.platform.is_macos:
      self.platform.sh_results.append(XCTRACE_DEVICES_SINGLE_OUTPUT)

    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = DriverConfig.parse("Unknown Device X")
    self.assertIn("Unknown Device X", str(cm.exception))

  def test_parse_adb_phone_identifier_multiple(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    with self.assertRaises(ArgumentTypeMultiException) as cm:
      _ = DriverConfig.parse("emulator.*")
    message: str = str(cm.exception)
    self.assertIn("emulator-5554", message)
    self.assertIn("emulator-5556", message)
    self.assertTrue(len(cm.exception), 1)
    self.assertTrue(cm.exception.matching(AmbiguousDriverIdentifier))
    self.assertEqual(len(self.platform.sh_cmds), 1)

  def test_parse_adb_phone_identifier(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT, ADB_DEVICES_OUTPUT]

    config = DriverConfig.parse("Nexus_7")
    assert isinstance(config, DriverConfig)
    self.assertEqual(len(self.platform.sh_cmds), 2)

    self.assertEqual(config.type, BrowserDriverType.ANDROID)
    self.assertEqual(config.device_id, "0a388e93")
    self.assertTrue(config.is_remote)
    self.assertFalse(config.is_local)

  def test_parse_adb_phone_serial(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT, ADB_DEVICES_OUTPUT]

    config = DriverConfig.parse("0a388e93")
    assert isinstance(config, DriverConfig)
    self.assertEqual(len(self.platform.sh_cmds), 2)

    self.assertEqual(config.type, BrowserDriverType.ANDROID)
    self.assertEqual(config.device_id, "0a388e93")

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
    self.assertEqual(config.device_id, "00001111-11AA22BB33DD")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
