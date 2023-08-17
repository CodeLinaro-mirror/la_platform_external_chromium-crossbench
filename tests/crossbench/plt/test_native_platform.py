# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import pathlib
import unittest

from crossbench import plt
from tests import test_helper


class PlatformTestCase(unittest.TestCase):

  def setUp(self):
    self.platform: plt.Platform = plt.PLATFORM

  def test_sleep(self):
    self.platform.sleep(0)
    self.platform.sleep(0.01)
    self.platform.sleep(dt.timedelta())
    self.platform.sleep(dt.timedelta(seconds=0.1))

  def test_cpu_details(self):
    details = self.platform.cpu_details()
    self.assertLess(0, details["physical cores"])

  def test_get_relative_cpu_speed(self):
    self.assertGreater(self.platform.get_relative_cpu_speed(), 0)

  def test_is_thermal_throttled(self):
    self.assertIsInstance(self.platform.is_thermal_throttled(), bool)

  def test_is_battery_powered(self):
    self.assertIsInstance(self.platform.is_battery_powered, bool)

  def test_cpu_usage(self):
    self.assertGreaterEqual(self.platform.cpu_usage(), 0)

  def test_system_details(self):
    self.assertIsNotNone(self.platform.system_details())

  def test_search_app_empty_path(self):
    with self.assertRaises(ValueError) as cm:
      self.platform.search_app(pathlib.Path())
    self.assertIn("empty", str(cm.exception))
    with self.assertRaises(ValueError) as cm:
      self.platform.search_app(pathlib.Path(""))
    self.assertIn("empty", str(cm.exception))


@unittest.skipIf(not plt.PLATFORM.is_win, "Incompatible platform")
class WinPlatformUnittest(PlatformTestCase):
  platform: plt.WinPlatform

  def setUp(self):
    super().setUp()
    assert isinstance(plt.PLATFORM, plt.WinPlatform)
    self.platform = plt.PLATFORM

  def test_sh(self):
    ls = self.platform.sh_stdout("ls")
    self.assertTrue(ls)

  def test_search_binary(self):
    with self.assertRaises(ValueError):
      self.platform.search_binary(pathlib.Path("does not exist"))
    path = self.platform.search_binary(
        pathlib.Path("Windows NT/Accessories/wordpad.exe"))
    self.assertTrue(path and path.exists())

  def test_app_version(self):
    path = self.platform.search_binary(
        pathlib.Path("Windows NT/Accessories/wordpad.exe"))
    self.assertTrue(path and path.exists())
    version = self.platform.app_version(path)
    self.assertIsNotNone(version)

  def test_is_macos(self):
    self.assertFalse(self.platform.is_macos)
    self.assertFalse(self.platform.is_linux)
    self.assertTrue(self.platform.is_win)
    self.assertFalse(self.platform.is_remote)

  def test_has_display(self):
    self.assertIn(self.platform.has_display, (True, False))


@unittest.skipIf(not plt.PLATFORM.is_posix, "Incompatible platform")
class PosixPlatformUnittest(PlatformTestCase):
  platform: plt.PosixPlatform

  def setUp(self):
    super().setUp()
    assert isinstance(plt.PLATFORM, plt.PosixPlatform)
    self.platform: plt.PosixPlatform = plt.PLATFORM

  def test_sh(self):
    ls = self.platform.sh_stdout("ls")
    self.assertTrue(ls)
    lsa = self.platform.sh_stdout("ls", "-a")
    self.assertTrue(lsa)
    self.assertNotEqual(ls, lsa)

  def test_which(self):
    ls_bin = self.platform.which("ls")
    bash_bin = self.platform.which("bash")
    self.assertNotEqual(ls_bin, bash_bin)
    self.assertTrue(pathlib.Path(ls_bin).exists())
    self.assertTrue(pathlib.Path(bash_bin).exists())

  def test_system_details(self):
    details = self.platform.system_details()
    self.assertTrue(details)

  def test_search_binary(self):
    result_path = self.platform.search_binary(pathlib.Path("ls"))
    self.assertIsNotNone(result_path)
    self.assertIn("ls", result_path.parts)


@unittest.skipIf(not plt.PLATFORM.is_macos, "Incompatible platform")
class MacOSPlatformHelperTestCase(PosixPlatformUnittest):
  platform: plt.MacOSPlatform

  def setUp(self):
    super().setUp()
    assert isinstance(plt.PLATFORM, plt.MacOSPlatform)
    self.platform = plt.PLATFORM

  def test_search_binary_not_found(self):
    binary = self.platform.search_binary(pathlib.Path("Invalid App Name"))
    self.assertIsNone(binary)
    binary = self.platform.search_binary(pathlib.Path("Non-existent App.app"))
    self.assertIsNone(binary)

  def test_search_binary(self):
    binary = self.platform.search_binary(pathlib.Path("Safari.app"))
    self.assertTrue(binary and binary.is_file())

  def test_search_app_invalid(self):
    with self.assertRaises(ValueError):
      self.platform.search_app(pathlib.Path("Invalid App Name"))

  def test_search_app_none(self):
    self.assertIsNone(self.platform.search_app(pathlib.Path("No App.app")))

  def test_search_app(self):
    binary = self.platform.search_app(pathlib.Path("Safari.app"))
    self.assertTrue(binary and binary.exists())
    self.assertTrue(binary and binary.is_dir())

  def test_app_version_app(self):
    app = self.platform.search_app(pathlib.Path("Safari.app"))
    self.assertIsNotNone(app)
    self.assertTrue(app.is_dir())
    version = self.platform.app_version(app)
    self.assertRegex(version, r"[0-9]+\.[0-9]+")

  def test_app_version_app_binary(self):
    binary = self.platform.search_binary(pathlib.Path("Safari.app"))
    self.assertIsNotNone(binary)
    self.assertTrue(binary.is_file())
    version = self.platform.app_version(binary)
    self.assertRegex(version, r"[0-9]+\.[0-9]+")

  def test_app_version_binary(self):
    binary = pathlib.Path("/usr/bin/safaridriver")
    self.assertTrue(binary.is_file())
    version = self.platform.app_version(binary)
    self.assertRegex(version, r"[0-9]+\.[0-9]+")

  def test_name(self):
    self.assertEqual(self.platform.name, "macos")

  def test_version(self):
    self.assertTrue(self.platform.version)
    self.assertRegex(self.platform.version, r"[0-9]+\.[0-9]")

  def test_device(self):
    self.assertTrue(self.platform.device)
    self.assertRegex(self.platform.device, r"[a-zA-Z]+[0-9]+,[0-9]+")

  def test_cpu(self):
    self.assertTrue(self.platform.cpu)
    self.assertRegex(self.platform.cpu, r".* [0-9]+ cores")

  def test_foreground_process(self):
    self.assertTrue(self.platform.foreground_process())

  def test_is_macos(self):
    self.assertTrue(self.platform.is_macos)
    self.assertFalse(self.platform.is_linux)
    self.assertFalse(self.platform.is_win)
    self.assertFalse(self.platform.is_remote)

  def test_set_main_screen_brightness(self):
    prev_level = plt.PLATFORM.get_main_display_brightness()
    brightness_level = 32
    plt.PLATFORM.set_main_display_brightness(brightness_level)
    self.assertEqual(brightness_level,
                     plt.PLATFORM.get_main_display_brightness())
    plt.PLATFORM.set_main_display_brightness(prev_level)
    self.assertEqual(prev_level, plt.PLATFORM.get_main_display_brightness())

  def test_check_autobrightness(self):
    self.platform.check_autobrightness()

  def test_exec_apple_script(self):
    self.assertEqual(
        self.platform.exec_apple_script('copy "a value" to stdout').strip(),
        "a value")

  def test_exec_apple_script_invalid(self):
    with self.assertRaises(plt.SubprocessError):
      self.platform.exec_apple_script('something is not right 11')


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
