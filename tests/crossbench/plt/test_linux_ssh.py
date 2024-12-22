# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from crossbench import path as pth
from crossbench import plt
from tests import test_helper
from tests.crossbench.plt.helper import BasePosixMockPlatformTestCase


class LinuxSshMockPlatformTestCase(BasePosixMockPlatformTestCase):
  __test__ = True
  HOST = "host"
  PORT = 9515
  SSH_PORT = 22
  SSH_USER = "user"
  platform: plt.LinuxSshPlatform

  def setUp(self) -> None:
    super().setUp()
    self.platform = plt.LinuxSshPlatform(
        self.mock_platform,
        host=self.HOST,
        port=self.PORT,
        ssh_port=self.SSH_PORT,
        ssh_user=self.SSH_USER)

  def test_is_linux(self):
    self.assertTrue(self.platform.is_linux)

  def test_is_remote_ssh(self):
    self.assertTrue(self.platform.is_remote_ssh)

  def test_basic_properties(self):
    self.assertTrue(self.platform.is_remote)
    self.assertEqual(self.platform.host, self.HOST)
    self.assertEqual(self.platform.port, self.PORT)
    self.assertIs(self.platform.host_platform, self.mock_platform)
    self.assertTrue(self.platform.is_posix)

  def test_name(self):
    self.assertEqual(self.platform.name, "linux_ssh")

  def test_version(self):
    self._expect_sh_ssh("uname -r", result="999")
    self.assertEqual(self.platform.version, "999")
    # Subsequent calls are cached.
    self.assertEqual(self.platform.version, "999")


  def test_iterdir(self):
    self._expect_sh_ssh("'[' -d parent_dir/child_dir ']'")
    self._expect_sh_ssh("ls -1 parent_dir/child_dir", result="file1\nfile2\n")

    self.assertSetEqual(
        set(self.platform.iterdir(pth.AnyWindowsPath("parent_dir\\child_dir"))),
        {
            pth.AnyPosixPath("parent_dir/child_dir/file1"),
            pth.AnyPosixPath("parent_dir/child_dir/file2")
        })

  def _expect_sh_ssh(self, *args, result=""):
    self.mock_platform.expect_sh(
        "ssh",
        "-p",
        str(self.SSH_PORT),
        f"{self.SSH_USER}@{self.HOST}",
        *args,
        result=result)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
