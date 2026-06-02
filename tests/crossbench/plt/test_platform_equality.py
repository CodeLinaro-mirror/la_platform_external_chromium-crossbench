# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest
from unittest import mock

from crossbench import path as pth
from crossbench import plt
from crossbench.plt.android_adb import Adb, AndroidAdbPlatform
from crossbench.plt.linux_ssh import LinuxSshPlatform
from tests import test_helper
from tests.crossbench.mock_helper import LinuxMockPlatform, MacOsMockPlatform


class PlatformEqualityTestCase(unittest.TestCase):

  def test_local_platform_equality(self) -> None:
    platform_1 = LinuxMockPlatform()
    platform_2 = LinuxMockPlatform()
    self.assertNotEqual(platform_1, platform_2)
    self.assertEqual(platform_1.key, platform_2.key)

    platform_3 = MacOsMockPlatform()
    self.assertNotEqual(platform_1.key, platform_3.key)

  def test_android_platform_equality(self) -> None:
    host_platform = mock.MagicMock(spec=plt.Platform)
    host_platform.is_remote = False

    adb_1 = mock.MagicMock(spec=Adb)
    adb_1.serial_id = "device_1"
    platform_1 = AndroidAdbPlatform(host_platform, adb=adb_1)

    adb_2 = mock.MagicMock(spec=Adb)
    adb_2.serial_id = "device_1"
    platform_2 = AndroidAdbPlatform(host_platform, adb=adb_2)

    adb_3 = mock.MagicMock(spec=Adb)
    adb_3.serial_id = "device_2"
    platform_3 = AndroidAdbPlatform(host_platform, adb=adb_3)

    self.assertNotEqual(platform_1, platform_2)
    self.assertEqual(platform_1.key, platform_2.key)
    self.assertNotEqual(platform_1.key, platform_3.key)

  def test_ssh_platform_equality(self) -> None:
    host_platform = mock.MagicMock(spec=plt.Platform)
    host_platform.is_remote = False

    # Patch _create_default_tmp_dir to avoid running remote command on init
    with mock.patch.object(
        LinuxSshPlatform,
        "_create_default_tmp_dir",
        return_value=pth.AnyPath("/tmp"),
    ):
      platform_1 = LinuxSshPlatform(
          host_platform, host="host1", port=22, ssh_port=22, ssh_user="user")
      platform_2 = LinuxSshPlatform(
          host_platform, host="host1", port=22, ssh_port=22, ssh_user="user")
      platform_3 = LinuxSshPlatform(
          host_platform, host="host2", port=22, ssh_port=22, ssh_user="user")
      platform_4 = LinuxSshPlatform(
          host_platform, host="host1", port=2222, ssh_port=22, ssh_user="user")

    self.assertNotEqual(platform_1, platform_2)
    self.assertEqual(platform_1.key, platform_2.key)

    self.assertNotEqual(platform_1.key, platform_3.key)
    self.assertNotEqual(platform_1.key, platform_4.key)

  def test_different_platform_types_not_equal(self) -> None:
    host_platform = mock.MagicMock(spec=plt.Platform)
    host_platform.is_remote = False

    local_platform = LinuxMockPlatform()

    adb = mock.MagicMock(spec=Adb)
    adb.serial_id = "device_1"
    android_platform = AndroidAdbPlatform(host_platform, adb=adb)

    with mock.patch.object(
        LinuxSshPlatform,
        "_create_default_tmp_dir",
        return_value=pth.AnyPath("/tmp"),
    ):
      ssh_platform = LinuxSshPlatform(
          host_platform, host="host1", port=22, ssh_port=22, ssh_user="user")

    self.assertNotEqual(local_platform.key, android_platform.key)
    self.assertNotEqual(local_platform.key, ssh_platform.key)
    self.assertNotEqual(android_platform.key, ssh_platform.key)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
