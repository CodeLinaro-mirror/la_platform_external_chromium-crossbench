# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import os
import pathlib
from unittest import mock

from crossbench import path as pth
from tests import test_helper
from tests.crossbench.mock_helper import WinMockPlatform
from tests.crossbench.plt.helper import BaseMockPlatformTestCase


class WinMockPlatformTestCase(BaseMockPlatformTestCase):
  __test__ = True

  def setUpMockPlatform(self):
    self.mock_platform = WinMockPlatform()
    self.platform = self.mock_platform

  def path(self, path: pth.AnyPathLike) -> pathlib.PureWindowsPath:
    return pathlib.PureWindowsPath(path)

  def test_is_win(self):
    self.assertTrue(self.platform.is_win)

  def test_path_conversion(self):
    self.assertIsInstance(
        self.platform.path("foo/bar"), pathlib.PureWindowsPath)
    self.assertIsInstance(
        self.platform.path(pathlib.PurePath("foo/bar")),
        pathlib.PureWindowsPath)
    self.assertIsInstance(
        self.platform.path(pathlib.PureWindowsPath("foo/bar")),
        pathlib.PureWindowsPath)
    self.assertIsInstance(
        self.platform.path(pathlib.PurePosixPath("foo/bar")),
        pathlib.PureWindowsPath)

  def test_which(self):
    bin_path = self.path("foo/bar/default/crossbench_mock_binary.exe")
    self.assertIsNone(self.platform.which(bin_path))
    with mock.patch("shutil.which", return_value=bin_path) as cm:
      self.assertEqual(self.platform.which(bin_path), bin_path)
    cm.assert_called_once_with(os.fspath(bin_path))

  def test_which_invalid(self):
    with self.assertRaises(ValueError) as cm:
      self.platform.which("")
    self.assertIn("empty", str(cm.exception))

  def test_search_binary_invalid(self):
    with self.assertRaises(ValueError) as cm:
      self.platform.search_binary("")
    self.assertIn("empty", str(cm.exception))
    with self.assertRaises(ValueError) as cm:
      self.platform.search_binary("foo/bar")
    self.assertIn(".exe", str(cm.exception))

  def test_search_binary_broken_which(self):
    bin_path = self.path("foo/bar/default/crossbench_mock_binary.exe")
    self.assertIsNone(self.platform.search_app(bin_path))
    with mock.patch("shutil.which", return_value=bin_path) as cm:
      with self.assertRaises(AssertionError) as search_cm:
        self.assertEqual(self.platform.search_app(bin_path), bin_path)
      self.assertIn("exist", str(search_cm.exception))
    cm.assert_called_once_with(os.fspath(bin_path))

  def test_search_binary(self):
    bin_path = self.path("foo/bar/default/crossbench_mock_binary.exe")
    self.assertIsNone(self.platform.search_app(bin_path))
    self.fs.create_file(bin_path, st_size=100)
    with mock.patch("shutil.which", return_value=bin_path) as cm:
      self.assertEqual(self.platform.search_app(bin_path), bin_path)
    cm.assert_called_once_with(os.fspath(bin_path))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
