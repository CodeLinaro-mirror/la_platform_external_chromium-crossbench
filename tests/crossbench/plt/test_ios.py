# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from pyfakefs.fake_filesystem import OSType
from typing_extensions import override

from crossbench.plt.ios import IOSPlatform
from tests import test_helper
from tests.crossbench.cli.config.base import (XCTRACE_DEVICES_NONE_OUTPUT,
                                              XCTRACE_DEVICES_OUTPUT,
                                              XCTRACE_DEVICES_SINGLE_OUTPUT)
from tests.crossbench.mock_helper import MacOsMockPlatform, ShResult
from tests.crossbench.plt.helper import BasePosixMockPlatformTestCase


class IOsMockPlatformTestCase(BasePosixMockPlatformTestCase):
  __test__ = True

  @override
  def setUp(self) -> None:
    super().setUp()
    self.fs.os = OSType.MACOS

  @override
  def mock_platform_setup(self) -> None:
    self.mock_platform = MacOsMockPlatform()
    self.expect_startup_devices()
    self.platform = IOSPlatform(self.mock_platform)

  def expect_startup_devices(self,
                             devices: ShResult
                             | str = XCTRACE_DEVICES_SINGLE_OUTPUT):
    self.mock_platform.expect_sh(
        "xcrun", "xctrace", "list", "devices", result=devices)

  def test_name(self):
    self.assertEqual(self.platform.name, "ios")

  def test_is_macos(self):
    self.assertTrue(self.platform.is_macos)

  def test_create_device_udid(self):
    self.expect_startup_devices()
    platform_a = IOSPlatform(self.mock_platform, "00001111-11AA22BB33DD")
    self.assertEqual(platform_a.udid, "00001111-11AA22BB33DD")
    self.expect_startup_devices()
    platform_b = IOSPlatform(self.mock_platform)
    self.assertEqual(platform_b.udid, "00001111-11AA22BB33DD")

  def test_create_device_udid_multiple(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.mock_platform, "00001111-11AA22BB33DD")
    self.assertEqual(platform_a.udid, "00001111-11AA22BB33DD")
    with self.assertRaises(ValueError):
      self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
      IOSPlatform(self.mock_platform)
    with self.assertRaises(ValueError):
      self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
      IOSPlatform(self.mock_platform, "invalid device id")

  def test_create_device_name(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    platform_a = IOSPlatform(self.mock_platform, "iPhone Pro")
    self.assertEqual(platform_a.udid, "00002222-11AA22BB33DD")

  def test_create_device_name_non_unique(self):
    self.expect_startup_devices(XCTRACE_DEVICES_OUTPUT)
    with self.assertRaisesRegex(ValueError, "2 devices"):
      IOSPlatform(self.mock_platform, "iPhone")

  def test_create_no_devices(self):
    self.expect_startup_devices(XCTRACE_DEVICES_NONE_OUTPUT)
    with self.assertRaisesRegex(ValueError, "No devices"):
      IOSPlatform(self.mock_platform, "iPhone")

  def test_uptime(self):
    # TODO: enable once all shell commands hare redirected to the host_platform.
    pass


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
