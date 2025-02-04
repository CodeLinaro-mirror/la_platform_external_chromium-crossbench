# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import argparse
import pathlib
import unittest
from unittest import mock

import crossbench.path as pth
from crossbench import plt
from crossbench.plt.posix import PosixPlatform
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.mock_helper import MockPlatform


class BaseMockPlatformTestCase(CrossbenchFakeFsTestCase, metaclass=abc.ABCMeta):
  __test__ = False
  platform: plt.Platform
  mock_platform: MockPlatform

  def setUp(self) -> None:
    super().setUp()
    self.mock_platform_setup()

  def mock_platform_str(self, platform, name) -> None:
    # Mock out str(platform) to avoid secondary errors when printing the
    # platform name in failing tests.
    patcher = mock.patch.object(type(platform), "__str__", return_value=name)
    self.addCleanup(patcher.stop)
    patcher.start()

  def mock_platform_setup(self):
    self.mock_platform = MockPlatform()  # pytype: disable=not-instantiable
    self.platform = self.mock_platform

  def tearDown(self):
    expected_sh_cmds = self.mock_platform.expected_sh_cmds
    if expected_sh_cmds is not None:
      self.assertListEqual(expected_sh_cmds, [],
                           "Got additional unused shell cmds.")
    super().tearDown()

  def expect_sh(self, *args, result=""):
    self.mock_platform.expect_sh(*args, result=result)

  def test_is_android(self):
    self.assertFalse(self.platform.is_android)

  def test_is_macos(self):
    self.assertFalse(self.platform.is_macos)

  def test_is_linux(self):
    self.assertFalse(self.platform.is_linux)

  def test_is_win(self):
    self.assertFalse(self.platform.is_win)

  def test_is_posix(self):
    self.assertFalse(self.platform.is_posix)

  def test_is_remote_ssh(self):
    self.assertFalse(self.platform.is_remote_ssh)

  def test_is_chromeos(self):
    self.assertFalse(self.platform.is_chromeos)

  def test_port_forward_invalid(self):
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "local_port"):
      self.platform.port_forward(-1, -1)

  def test_reverse_port_forward_invalid(self):
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "remote_port"):
      self.platform.reverse_port_forward(-1, -1)


class BaseLocalMockPlatformTestMixin:

  def test_local_port_forward_invalid(self):
    with self.assertRaisesRegex(ValueError, "local platform"):
      self.platform.port_forward(1000, 2000)

  def test_local_reverse_port_forward_invalid(self):
    with self.assertRaisesRegex(ValueError, "local platform"):
      self.platform.reverse_port_forward(1000, 2000)

  def test_local_reverse_port_forward(self):
    port = self.platform.get_free_port()
    self.assertEqual(self.platform.reverse_port_forward(port, port), port)
    self.platform.stop_reverse_port_forward(port)

  def test_local_port_forward(self):
    port = self.platform.get_free_port()
    self.assertEqual(self.platform.port_forward(port, port), port)
    self.platform.stop_port_forward(port)


class BasePosixMockPlatformTestCase(BaseMockPlatformTestCase):
  platform: PosixPlatform

  def tearDown(self) -> None:
    assert isinstance(self.platform, PosixPlatform)
    super().tearDown()

  def test_is_posix(self):
    self.assertTrue(self.platform.is_posix)

  def test_path_conversion(self):
    self.assertIsInstance(self.platform.path("foo/bar"), pathlib.PurePosixPath)
    self.assertIsInstance(
        self.platform.path(pathlib.PurePath("foo/bar")), pathlib.PurePosixPath)
    self.assertIsInstance(
        self.platform.path(pathlib.PureWindowsPath("foo/bar")),
        pathlib.PurePosixPath)
    self.assertIsInstance(
        self.platform.path(pathlib.PurePosixPath("foo/bar")),
        pathlib.PurePosixPath)

  @unittest.skipUnless(plt.PLATFORM.is_win, "Incompatible platform")
  def test_win_absolute_path_conversion(self):
    windows_path = pth.AnyWindowsPath("/foo/bar/file")
    abs_path = self.platform.absolute(windows_path)
    self.assertEqual(str(abs_path), "/foo/bar/file")
    self.assertIsInstance(abs_path, pth.AnyPosixPath)
    self.assertTrue(abs_path.is_absolute())
    self.assertTrue(self.platform.is_absolute(abs_path))

  @unittest.skipUnless(plt.PLATFORM.is_win, "Incompatible platform")
  def test_win_absolute_path_conversion_drive(self):
    windows_path = pth.AnyWindowsPath("C:/foo/bar/file")
    abs_path = self.platform.absolute(windows_path)
    self.assertEqual(str(abs_path), "/foo/bar/file")
    self.assertIsInstance(abs_path, pth.AnyPosixPath)
    self.assertTrue(abs_path.is_absolute())
    self.assertTrue(self.platform.is_absolute(abs_path))
