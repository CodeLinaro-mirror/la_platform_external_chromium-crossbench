# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pytest

from crossbench import plt
from crossbench.plt.android_adb import Adb, AndroidAdbPlatform
from tests import test_helper
from tests.crossbench.plt.test_native_platform import \
    PosixNativePlatformTestCase


@pytest.fixture(scope="class")
def adb_unittest_fixtures(request, device_id, adb_path):
  request.cls.device_id = device_id
  request.cls.adb_path = adb_path


@pytest.mark.usefixtures("adb_unittest_fixtures")
class AndroidAdbPlatformTestCase(PosixNativePlatformTestCase):

  def setUp(self):
    super().setUp()
    assert hasattr(self, "device_id")
    assert hasattr(self, "adb_path")
    self.adb = Adb(plt.PLATFORM, self.device_id, self.adb_path)
    self.platform: AndroidAdbPlatform = AndroidAdbPlatform(
        plt.PLATFORM, adb=self.adb)
    assert self.platform.is_android
    self.known_binary = "dumpsys"

  def test_app_version(self):
    with self.assertRaises(ValueError):
      self.platform.app_version("path/to/invalid/test/crossbench/bin")
    version = self.platform.app_version("com.android.chrome")
    self.assertTrue(version)

  def test_is_battery_powered(self):
    self.assertIs(self.platform.is_battery_powered, False)

  def test_home(self):
    if self.adb.has_root():
      self.assertTrue(self.platform.is_dir(self.platform.home()))

  def test_cpu_usage(self):
    self.skipTest("Not supported yet")


del PosixNativePlatformTestCase

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
