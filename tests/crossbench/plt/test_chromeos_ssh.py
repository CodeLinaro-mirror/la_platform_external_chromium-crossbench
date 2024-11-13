# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations
import pathlib

from crossbench.plt.chromeos_ssh import ChromeOsSshPlatform
from tests import test_helper
from tests.crossbench.plt.test_linux_ssh import LinuxSshMockPlatformTestCase


class ChromeOsSshMockPlatformTestCase(LinuxSshMockPlatformTestCase):
  SSH_USER = "chronos"
  platform: ChromeOsSshPlatform

  def setUp(self) -> None:
    super().setUp()
    self.platform = ChromeOsSshPlatform(
        self.mock_platform,
        host=self.HOST,
        port=self.PORT,
        ssh_port=self.SSH_PORT,
        ssh_user=self.SSH_USER)

  def test_name(self):
    self.assertEqual(self.platform.name, "chromeos_ssh")

  def test_is_chromeos(self):
    self.assertTrue(self.platform.is_chromeos)

  def test_basic_properties(self):
    super().test_basic_properties()
    self.assertEqual(self.platform.default_tmp_dir,
                     pathlib.PurePosixPath("/usr/local/tmp/"))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
