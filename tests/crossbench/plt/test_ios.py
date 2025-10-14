# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt

from pyfakefs.fake_filesystem import OSType
from typing_extensions import override

from crossbench import path as pth
from crossbench.plt.ios import IOSPlatform
from crossbench.plt.version import PlatformVersion
from tests import test_helper
from tests.crossbench.cli.config.base import XCTRACE_DEVICES_NONE_OUTPUT, \
    XCTRACE_DEVICES_OUTPUT, XCTRACE_DEVICES_SINGLE_OUTPUT
from tests.crossbench.mock_helper import MacOsMockPlatform, ShResult
from tests.crossbench.plt.helper import BaseMockPlatformTestCase


class IOsMockPlatformTestCase(BaseMockPlatformTestCase):
  __test__ = True

  SAFARI_PATH = "/Applications/Safari.app"

  @override
  def setUp(self) -> None:
    super().setUp()
    self.fs.os = OSType.MACOS

  @override
  def setup_host_platform(self) -> MacOsMockPlatform:
    return MacOsMockPlatform()

  @override
  def setup_platform(self) -> IOSPlatform:
    self.expect_startup_devices()
    return IOSPlatform(self.host_platform)

  def expect_startup_devices(self,
                             devices: ShResult
                             | str = XCTRACE_DEVICES_SINGLE_OUTPUT):
    self.host_platform.expect_sh(
        "xcrun", "xctrace", "list", "devices", result=devices)

  def test_name(self):
    self.assertEqual(self.platform.name, "ios")

  def test_is_ios(self):
    self.assertTrue(self.platform.is_ios)

  def test_is_apple(self):
    self.assertTrue(self.platform.is_apple)

  def test_create_device_udid(self):
    self.expect_startup_devices()
    platform_a = IOSPlatform(self.host_platform, "00001111-11AA22BB33DD")
    self.assertEqual(platform_a.udid, "00001111-11AA22BB33DD")
    self.expect_startup_devices()
    platform_b = IOSPlatform(self.host_platform)
    self.assertEqual(platform_b.udid, "00001111-11AA22BB33DD")

  def test_create_device_udid_multiple(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "00001111-11AA22BB33DD")
    self.assertEqual(platform_a.udid, "00001111-11AA22BB33DD")
    with self.assertRaises(ValueError):
      self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
      IOSPlatform(self.host_platform)
    with self.assertRaises(ValueError):
      self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
      IOSPlatform(self.host_platform, "invalid device id")

  def test_create_device_name(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "iPhone Pro")
    self.assertEqual(platform_a.udid, "00002222-11AA22BB33DD")

  def test_create_device_name_non_unique(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    with self.assertRaisesRegex(ValueError, "2 devices"):
      IOSPlatform(self.host_platform, "iPhone")

  def test_create_no_devices(self):
    self.expect_startup_devices(XCTRACE_DEVICES_NONE_OUTPUT)
    with self.assertRaisesRegex(ValueError, "No devices"):
      IOSPlatform(self.host_platform, "iPhone")

  def test_uptime(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "iPhone Pro")
    self.assertEqual(platform_a.uptime(), dt.timedelta())

  def test_search_binary_safari(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "iPhone Pro")
    self.assertEqual(
        platform_a.search_binary(self.SAFARI_PATH),
        pth.AnyPath(self.SAFARI_PATH))

  def test_search_binary_not_safari(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "iPhone Pro")
    with self.assertRaisesRegex(ValueError, "Safari is the only supported app"):
      platform_a.search_binary("/usr/bin/safaridriver")

  def test_is_file_safari(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "iPhone Pro")
    self.assertTrue(platform_a.is_file(self.SAFARI_PATH))

  def test_is_file_not_safari(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "iPhone Pro")
    with self.assertRaisesRegex(ValueError, "Safari is the only supported app"):
      platform_a.is_file("/usr/bin/safaridriver")

  def test_app_version_safari(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "iPhone Pro")
    self.assertEqual(platform_a.app_version(self.SAFARI_PATH), "17.1.1")

  def test_app_version_not_safari(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "iPhone Pro")
    with self.assertRaisesRegex(ValueError, "Safari is the only supported app"):
      platform_a.app_version("/usr/bin/safaridriver")

  def test_process_children(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "iPhone Pro")
    self.assertEqual(platform_a.process_children(123), [])

  def test_os_details(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "iPhone Pro")
    self.assertEqual(
        platform_a.os_details(), {
            "system": "ios",
            "platform": "ios 17.1.1",
            "version": "17.1.1",
            "release": "17.1.1"
        })

  def test_version(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.host_platform, "iPhone Pro")
    self.assertEqual(platform_a.version, PlatformVersion([17, 1, 1]))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
