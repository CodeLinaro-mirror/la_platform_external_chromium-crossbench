# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
from unittest import mock

import hjson

from crossbench import plt
from crossbench.cli.config.driver import AmbiguousDriverIdentifier, DriverConfig
from crossbench.cli.config.driver_type import BrowserDriverType
from crossbench.exception import ArgumentTypeMultiException
from crossbench.plt.android_adb import AndroidAdbPlatform
from crossbench.plt.chromeos_ssh import ChromeOsSshPlatform
from tests import test_helper
from tests.crossbench.cli.config.base import (
  ADB_DEVICES_OUTPUT,
  IOS_DEVICES_SINGLE_OUTPUT,
  BaseConfigTestCase,
)
from tests.crossbench.mock_helper import ShResult


class DriverConfigTestCase(BaseConfigTestCase):
  def test_default(self):
    default = DriverConfig.default()
    self.assertEqual(default.driver_type, BrowserDriverType.WEB_DRIVER)
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
    self.assertIn("/driver", str(cm.exception))

    self.fs.create_file(driver_path)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = DriverConfig.parse(str(driver_path))
    message = str(cm.exception)
    self.assertIn("/driver", message)
    self.assertIn("empty", message)

  def test_parse_driver_path(self):
    chromedriver_path = (self.out_dir / "chromedriver").resolve()
    self.fs.create_file(chromedriver_path, contents="binary data")
    driver = DriverConfig.parse(str(chromedriver_path))
    self.assertEqual(str(driver.path), str(chromedriver_path))

    config = {"path": str(chromedriver_path)}
    driver_2 = DriverConfig.parse(config)
    self.assertEqual(driver_2.path, chromedriver_path)
    self.assertEqual(driver, driver_2)

    driver_3 = DriverConfig.parse(chromedriver_path)
    self.assertEqual(driver_3.path, chromedriver_path)
    self.assertEqual(driver, driver_3)

  def test_parse_driver_path_unresolved(self):
    chromedriver_path = self.out_dir / "chromedriver"
    expected_chromedriver_path = r".*\/chromedriver"
    self.fs.create_file(chromedriver_path, contents="binary data")
    driver = DriverConfig.parse(str(chromedriver_path))
    self.assertRegex(str(driver.path), expected_chromedriver_path)

    config = {"path": str(chromedriver_path)}
    driver_2 = DriverConfig.parse(config)
    self.assertRegex(str(driver_2.path), expected_chromedriver_path)

  def test_parse_dict_device_id_conflict(self):
    self.platform.sh_results = []
    config_dict = {
      "type": "adb",
      "device_id": "1234",
      "settings": {
        "device_id": "ABCD",
      },
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
        "ssh_user": "root",
      },
    }
    ssh_user = config_dict["settings"]["ssh_user"]
    ssh_host = config_dict["settings"]["host"]
    self.platform.expect_sh(
      "ssh",
      *ChromeOsSshPlatform.SSH_OPTIONS,
      "-p",
      config_dict["settings"]["ssh_port"],
      f"{ssh_user}@{ssh_host}",
      f"'[' -e {ChromeOsSshPlatform.AUTOLOGIN_PATH} ']'",
    )
    config = DriverConfig.parse(config_dict)
    assert isinstance(config, DriverConfig)
    self.assertEqual(config.driver_type, BrowserDriverType.CHROMEOS_SSH)
    self.assertTrue(config.is_remote)
    self.assertFalse(config.is_local)
    platform = config.get_platform()
    assert isinstance(platform, ChromeOsSshPlatform)
    self.assertEqual(platform.host, "chromeos6-row17-rack14-host7")
    self.assertEqual(platform.port, 9515)
    self.assertEqual(platform.ssh_port, 22)
    self.assertEqual(platform.ssh_user, "root")

  def test_parse_inline_json_adb(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    config_dict: dict[str, object] = {
      "type": "adb",
      "settings": {
        "device_id": "0a388e93",
      },
    }
    config_1 = DriverConfig.parse(hjson.dumps(config_dict))
    self.assertIsInstance(config_1, DriverConfig)
    self.assertEqual(config_1.driver_type, BrowserDriverType.ANDROID)
    self.assertEqual(config_1.device_id, "0a388e93")
    self.assertIsNotNone(config_1.settings)
    self.assertEqual(config_1.settings["device_id"], "0a388e93")
    self.assertFalse(config_1.is_remote)
    self.assertTrue(config_1.is_local)
    self.assertTrue(config_1.driver_type.is_remote_browser)
    self.assertFalse(config_1.driver_type.is_local_browser)
    self.assertIsNone(config_1.adb_bin)

    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    config_2 = DriverConfig.parse_dict(config_dict)
    self.assertIsInstance(config_2, DriverConfig)
    self.assertEqual(config_2.driver_type, BrowserDriverType.ANDROID)
    self.assertEqual(config_2.device_id, "0a388e93")
    self.assertIsNotNone(config_2.settings)
    self.assertEqual(config_2.settings["device_id"], "0a388e93")
    self.assertFalse(config_2.is_remote)
    self.assertTrue(config_2.is_local)
    self.assertTrue(config_2.driver_type.is_remote_browser)
    self.assertFalse(config_2.driver_type.is_local_browser)
    self.assertIsNone(config_2.adb_bin)
    self.assertEqual(config_1, config_2)

    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    config_dict = {"type": "adb", "device_id": "0a388e93"}
    config_3 = DriverConfig.parse_dict(config_dict)
    assert isinstance(config_3, DriverConfig)
    self.assertEqual(config_3.driver_type, BrowserDriverType.ANDROID)
    self.assertEqual(config_3.device_id, "0a388e93")
    self.assertFalse(config_3.is_remote)
    self.assertTrue(config_3.is_local)
    self.assertTrue(config_3.driver_type.is_remote_browser)
    self.assertFalse(config_3.driver_type.is_local_browser)
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
      "adb_bin": str(adb_bin),
    }
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = DriverConfig.parse(hjson.dumps(config_dict))
    self.assertIn(str(adb_bin), str(cm.exception))
    self.fs.create_file(adb_bin, st_size=100)
    config = DriverConfig.parse(hjson.dumps(config_dict))
    assert isinstance(config, DriverConfig)
    self.assertEqual(config.driver_type, BrowserDriverType.ANDROID)
    self.assertEqual(config.adb_bin, adb_bin)

  def test_parse_adb_phone_identifier_unknown(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]

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

    self.assertEqual(config.driver_type, BrowserDriverType.ANDROID)
    self.assertEqual(config.device_id, "0a388e93")
    self.assertFalse(config.is_remote)
    self.assertTrue(config.is_local)

  def test_parse_adb_phone_serial(self):
    self.platform.sh_results = [ADB_DEVICES_OUTPUT, ADB_DEVICES_OUTPUT]

    config = DriverConfig.parse("0a388e93")
    assert isinstance(config, DriverConfig)
    self.assertEqual(len(self.platform.sh_cmds), 2)

    self.assertEqual(config.driver_type, BrowserDriverType.ANDROID)
    self.assertEqual(config.device_id, "0a388e93")

  def test_parse_ios_phone_serial(self):
    if not plt.PLATFORM.is_macos:
      return
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]

    with mock.patch(
      "crossbench.cli.config.driver.ios_devices",
      return_value=IOS_DEVICES_SINGLE_OUTPUT,
    ):
      config = DriverConfig.parse("00001111-11AA22BB33DD")
    assert isinstance(config, DriverConfig)
    self.assertEqual(len(self.platform.sh_cmds), 1)

    self.assertEqual(config.driver_type, BrowserDriverType.IOS)
    self.assertEqual(config.device_id, "00001111-11AA22BB33DD")

  def test_parse_custom_bundletool(self):
    adb_bin = self.out_dir / "adb"
    bundletool = self.out_dir / "bundletool"
    self.platform.sh_results = [ADB_DEVICES_OUTPUT]
    config_dict = {
      "type": "adb",
      "device_id": "0a388e93",
      "adb_bin": str(adb_bin),
      "bundletool": str(bundletool),
    }
    self.fs.create_file(adb_bin, st_size=100)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = DriverConfig.parse(hjson.dumps(config_dict))
    self.assertIn(str(bundletool), str(cm.exception))
    self.fs.create_file(bundletool, st_size=100)
    config = DriverConfig.parse(hjson.dumps(config_dict))
    assert isinstance(config, DriverConfig)
    self.assertEqual(config.driver_type, BrowserDriverType.ANDROID)
    self.assertEqual(config.bundletool, bundletool)

  def test_parse_adb_tcp_defers_auto_connect_to_get_platform(self) -> None:
    serial = "192.168.0.5:5555"
    config_dict: dict[str, object] = {"type": "adb", "device_id": serial}
    config = DriverConfig.parse_dict(config_dict)
    self.assertEqual(config.driver_type, BrowserDriverType.ANDROID)
    self.assertEqual(config.device_id, serial)

    short_config = DriverConfig.parse(serial)
    self.assertEqual(short_config.driver_type, BrowserDriverType.ANDROID)
    self.assertEqual(short_config.device_id, serial)

    ipv6_config = DriverConfig.parse("[::1]:5555")
    self.assertEqual(ipv6_config.driver_type, BrowserDriverType.ANDROID)
    self.assertEqual(ipv6_config.device_id, "[::1]:5555")
    self.assertEqual(len(self.platform.sh_cmds), 0)

    sh_results = [
      ShResult(""),
      ShResult("List of devices attached\n"),
      ShResult(f"connected to {serial}\n"),
      ShResult(
        "List of devices attached\n"
        f"{serial} device product:brya model:mica device:mica\n"
      ),
    ]
    if self.platform.is_macos:
      sh_results.insert(0, ShResult(returncode=1))
    self.platform.sh_results = sh_results
    adb_platform = short_config.get_platform()
    assert isinstance(adb_platform, AndroidAdbPlatform)
    self.assertEqual(adb_platform.adb.serial_id, serial)

  def test_parse_adb_bypass_oobe(self) -> None:
    sh_results = [
      ADB_DEVICES_OUTPUT,
      ShResult(""),
      ADB_DEVICES_OUTPUT,
    ]
    if self.platform.is_macos:
      sh_results.insert(1, ShResult(returncode=1))
    self.platform.sh_results = list(sh_results)
    default_config = DriverConfig.parse_dict(
      {
        "type": "adb",
        "device_id": "0a388e93",
      }
    )
    self.assertIsNone(default_config.settings)
    default_platform = default_config.get_adb_platform()
    self.assertIsInstance(default_platform, AndroidAdbPlatform)
    assert isinstance(default_platform, AndroidAdbPlatform)
    self.assertTrue(default_platform.bypass_oobe)

    self.platform.sh_results = list(sh_results)
    disabled_config = DriverConfig.parse_dict(
      {
        "type": "adb",
        "device_id": "0a388e93",
        "settings": {
          "bypass_oobe": False,
        },
      }
    )
    assert disabled_config.settings is not None
    self.assertFalse(disabled_config.settings["bypass_oobe"])
    disabled_platform = disabled_config.get_adb_platform()
    self.assertIsInstance(disabled_platform, AndroidAdbPlatform)
    assert isinstance(disabled_platform, AndroidAdbPlatform)
    self.assertFalse(disabled_platform.bypass_oobe)

    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      DriverConfig.parse_dict(
        {
          "type": "adb",
          "device_id": "0a388e93",
          "settings": {
            "bypass_oobe": "invalid",
          },
        }
      )
    self.assertIn("bypass_oobe", str(cm.exception))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
