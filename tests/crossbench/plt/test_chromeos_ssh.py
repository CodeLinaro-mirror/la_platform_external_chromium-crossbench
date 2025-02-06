# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations
import pathlib

from typing_extensions import override

from crossbench.plt.chromeos_ssh import ChromeOsSshPlatform
from tests import test_helper
from tests.crossbench.plt.test_linux_ssh import LinuxSshMockPlatformTestCase


class ChromeOsSshMockPlatformTestCase(LinuxSshMockPlatformTestCase):
  SSH_USER = "chronos"
  platform: ChromeOsSshPlatform

  @override
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

  def test_display_resolution(self):
    cros_health_tool_out = '''
    {
      "embedded_display": {
        "display_height": "140",
        "display_name": "NV116WHM-T14",
        "display_width": "260",
        "edid_version": "1.4",
        "input_type": "Digital",
        "manufacture_week": 1,
        "manufacture_year": 2019,
        "manufacturer": "BOE",
        "model_id": 2303,
        "privacy_screen_enabled": false,
        "privacy_screen_supported": false,
        "refresh_rate": 59.99822202162979,
        "resolution_horizontal": "1366",
        "resolution_vertical": "768"
      }
    }'''
    self._expect_sh_ssh(
        "cros-health-tool telem --category=display",
        result=cros_health_tool_out)
    [horizontal, vertical] = self.platform.display_resolution()
    self.assertEqual(horizontal, 1366)
    self.assertEqual(vertical, 768)

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
