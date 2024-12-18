# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import contextlib
import os
from unittest import mock

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
    self.host_platform = self.mock_platform
    self.platform = plt.LinuxSshPlatform(
        self.mock_platform,
        host=self.HOST,
        port=self.PORT,
        ssh_port=self.SSH_PORT,
        ssh_user=self.SSH_USER)
    self.mock_platform_str(self.platform, "linux_ssh_mock_platform")

  def _expect_sh_ssh(self, *args, result=""):
    self.mock_platform.expect_sh(
        "ssh",
        "-p",
        str(self.SSH_PORT),
        f"{self.SSH_USER}@{self.HOST}",
        *args,
        result=result)

  def _expect_sh_ssh_shell(self, *args, result=""):
    cmd_string = f"ssh -p {str(self.SSH_PORT)} {self.SSH_USER}@{self.HOST} "

    for arg in args:
      cmd_string += arg + " "

    self.mock_platform.expect_sh(cmd_string, result=result)

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

  def test_cat_file(self):
    self._expect_sh_ssh("cat path/to/a/file")
    self.platform.cat(self.platform.path("path/to/a/file"))
    self._expect_sh_ssh("cat 'path/with a space/to/a/file'")
    self.platform.cat(self.platform.path("path/with a space/to/a/file"))

  def test_sh_shell_invalid(self):
    with self.assertRaisesRegex(ValueError, "shell=True"):
      self.platform.sh_stdout("ls", "folder with space", shell=True)

  def test_sh_shell(self):
    self._expect_sh_ssh("ls sdcard", result="FILE1\nFILE2\n")
    self.assertEqual(self.platform.sh_stdout("ls", "sdcard"), "FILE1\nFILE2\n")

    self._expect_sh_ssh("ls 'folder with space'", result="FOLDER\n")
    self.assertEqual(
        self.platform.sh_stdout("ls", "folder with space"), "FOLDER\n")

    self._expect_sh_ssh("'ls foo && ls bar'", result="FILE1\nFILE2\n")
    self.assertEqual(
        self.platform.sh_stdout("ls foo && ls bar"), "FILE1\nFILE2\n")

    self._expect_sh_ssh_shell("'ls foo && ls bar'", result="FILE1\nFILE2\n")
    self.assertEqual(
        self.platform.sh_stdout("ls foo && ls bar", shell=True),
        "FILE1\nFILE2\n")

    self._expect_sh_ssh("ls foo '&&' ls bar", result="FILE1\nFILE2\n")
    self.assertEqual(
        self.platform.sh_stdout("ls", "foo", "&&", "ls", "bar"),
        "FILE1\nFILE2\n")

  @contextlib.contextmanager
  def mock_popen(self, platform):
    with mock.patch.object(type(platform), "popen") as patcher:
      yield patcher

  @contextlib.contextmanager
  def mock_get_free_port(self, platform, port):
    with mock.patch.object(
        type(platform), "get_free_port", return_value=port) as patcher:
      yield patcher

  @contextlib.contextmanager
  def mock_wait_for_port(self, platform):
    with mock.patch.object(type(platform), "wait_for_port") as patcher:
      yield patcher

  def test_port_forward(self):
    with self.mock_popen(
        self.host_platform) as mock_popen, self.mock_wait_for_port(
            self.host_platform) as mock_wait_for_port:
      port = self.platform.port_forward(666, 33221)
    mock_popen.assert_called_once()
    mock_wait_for_port.assert_called_once()
    self.assertEqual(port, 666)
    with self.assertRaisesRegex(RuntimeError, "twice"):
      port = self.platform.port_forward(666, 33221)
    self.platform.stop_port_forward(port)

  def test_port_forward_auto_port(self):
    with self.mock_get_free_port(self.host_platform, 666) as mock_free_port:
      with self.mock_popen(self.host_platform) as mock_popen:
        with self.mock_wait_for_port(self.host_platform) as mock_wait_for_port:
          port = self.platform.port_forward(0, 33221)
      mock_popen.assert_called_once()
      mock_wait_for_port.assert_called_once()
    mock_free_port.assert_called_once()
    self.assertEqual(port, 666)
    with self.assertRaisesRegex(RuntimeError, "twice"):
      port = self.platform.port_forward(666, 33221)
    self.platform.stop_port_forward(port)

  def test_reverse_port_forward(self):
    self._expect_sh_ssh("ss -HOlnt sport = 666", result="666")
    with self.mock_popen(self.host_platform) as mock_popen:
      port = self.platform.reverse_port_forward(666, 33221)
    mock_popen.assert_called_once()
    with self.assertRaisesRegex(RuntimeError, "twice"):
      self.platform.reverse_port_forward(666, 33221)
    self.assertEqual(port, 666)
    self.platform.stop_reverse_port_forward(port)

  def test_push_creates_dest_dir(self):
    self._expect_sh_ssh("mkdir -p remote/dest/path")
    self.mock_platform.expect_sh(
        "scp", "-P", self.SSH_PORT, "source/path/file",
        f"{self.SSH_USER}@{self.HOST}:remote/dest/path/file")
    self.platform.push(
        self.platform.path("source/path/file"),
        self.platform.path("remote/dest/path/file"))

  def test_pull_creates_dest_dir(self):
    self.mock_platform.expect_sh(
        "scp", "-P", self.SSH_PORT,
        f"{self.SSH_USER}@{self.HOST}:remote/source/path/file",
        "local/dest/path/file")
    self.platform.pull(
        self.platform.path("remote/source/path/file"),
        self.platform.path("local/dest/path/file"))

    self.assertEqual(self.mock_platform.mkdir_calls, 1)
    self.assertTrue(os.path.exists("local/dest/path"))

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
