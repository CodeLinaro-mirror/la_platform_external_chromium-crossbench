# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import crossbench.path as pth
from crossbench.plt import PLATFORM
from crossbench.plt.bin import (Binary, BinaryNotFoundError, LinuxBinary,
                                MacOsBinary, PosixBinary, WinBinary)
from tests import test_helper
from tests.crossbench.mock_helper import (AndroidAdbMockPlatform,
                                          CrossbenchFakeFsTestCase,
                                          LinuxMockPlatform, MacOsMockPlatform,
                                          MockAdb, WinMockPlatform)


class BinaryTestCase(CrossbenchFakeFsTestCase):

  def setUp(self) -> None:
    super().setUp()
    self._all_mock_platforms = (
        LinuxMockPlatform(),
        MacOsMockPlatform(),
        WinMockPlatform(),
        # TODO: add adb testing
    )
    self._all_platforms = (PLATFORM,) + self._all_mock_platforms

  def all_mock_platforms(self):
    for platform in self._all_mock_platforms:
      with self.subTest(platform=platform):
        yield platform

  def all_platforms(self):
    for platform in self._all_platforms:
      with self.subTest(platform=platform):
        yield platform

  def create_binary_path(self, path: str) -> pth.LocalPath:
    result = pth.LocalPath(path)
    self.fs.create_file(result, st_size=100)
    return result

  def test_create_without_binary(self):
    with self.assertRaises(ValueError):
      Binary(name="test")
    with self.assertRaises(ValueError):
      Binary(name="test", posix="")

  def test_new_windows_binary_invalid(self):
    with self.assertRaises(ValueError):
      WinBinary("custom")
    with self.assertRaises(ValueError):
      WinBinary(pth.RemotePath("custom"))
    with self.assertRaises(ValueError):
      WinBinary(pth.RemotePath("foo/bar/custom.py"))

  def test_new_windows_binary(self):
    binary = WinBinary("crossbench_mock_binary.exe")
    self.assertEqual(binary.name, "crossbench_mock_binary.exe")
    platform = WinMockPlatform()
    path = platform.path("C:/Users/user-name/AppData/Local/Programs/"
                         "crossbench/crossbench_mock_binary.exe")
    with self.assertRaises(ValueError):
      with platform.override_binary(binary, path):
        self.assertEqual(binary.resolve(platform), path)
    self.fs.create_file(path, st_size=100)
    with platform.override_binary(binary, path):
      self.assertEqual(binary.resolve(platform), path)
      self.assertEqual(binary.resolve_cached(platform), path)

    # Still cached
    self.assertEqual(binary.resolve_cached(platform), path)
    with self.assertRaises(BinaryNotFoundError):
      self.assertEqual(binary.resolve(platform), path)

    binary.resolve_cached.cache_clear()
    with self.assertRaises(BinaryNotFoundError):
      self.assertEqual(binary.resolve(platform), path)
    with self.assertRaises(BinaryNotFoundError):
      self.assertEqual(binary.resolve_cached(platform), path)

  def test_basic_accessor(self):
    binary = Binary("test", default="foo/bar/test")
    self.assertEqual(binary.name, "test")

  def test_unknown_binary(self):
    binary = Binary("crossbench_mock_binary", default="crossbench_mock_binary")
    for platform in self.all_platforms():
      with self.assertRaises(BinaryNotFoundError):
        binary.resolve(platform)

  def test_known_binary_default(self):
    for platform in self.all_mock_platforms():
      default = pth.LocalPath("foo/bar/default/crossbench_mock_binary")
      result = default
      if platform.is_win:
        result = pth.LocalPath("foo/bar/default/crossbench_mock_binary.exe")
      binary = Binary("crossbench_mock_binary", default=default)
      self.assertEqual(binary.platform_path(platform), pth.RemotePath(result))
      with self.assertRaises(BinaryNotFoundError):
        binary.resolve(platform)
      with self.assertRaises(BinaryNotFoundError):
        binary.resolve_cached(platform)
      self.fs.create_file(result, st_size=100)
      self.assertEqual(binary.resolve(platform), result)
      self.assertEqual(binary.resolve_cached(platform), result)
      result.unlink()

  def test_known_binary_linux(self):
    result = self.create_binary_path("foo/bar/default/crossbench_mock_binary")
    binary = Binary("crossbench_mock_binary", linux=result)
    self.validate_known_binary_linux(result, binary)
    binary = LinuxBinary(result)
    self.validate_known_binary_linux(result, binary)

  def validate_known_binary_linux(self, result, binary):
    platform = LinuxMockPlatform()
    self.assertEqual(binary.resolve(platform), result)
    self.assertEqual(binary.resolve_cached(platform), result)

    for platform in self.all_mock_platforms():
      if platform.is_linux:
        continue
      self.assertIsNone(binary.platform_path(platform))
      with self.assertRaises(BinaryNotFoundError):
        binary.resolve(platform)
      with self.assertRaises(BinaryNotFoundError):
        binary.resolve_cached(platform)

  def test_known_binary_macos(self):
    result = self.create_binary_path("foo/bar/default/crossbench_mock_binary")
    binary = Binary("crossbench_mock_binary", macos=result)
    self.validate_known_binary_macos(result, binary)
    binary = MacOsBinary(result)
    self.validate_known_binary_macos(result, binary)

  def validate_known_binary_macos(self, result, binary):
    platform = MacOsMockPlatform()
    self.assertEqual(binary.resolve(platform), result)
    self.assertEqual(binary.resolve_cached(platform), result)

    for platform in self.all_mock_platforms():
      if platform.is_macos:
        continue
      self.assertIsNone(binary.platform_path(platform))
      with self.assertRaises(BinaryNotFoundError):
        binary.resolve(platform)
      with self.assertRaises(BinaryNotFoundError):
        binary.resolve_cached(platform)

  def test_known_binary_posix(self):
    result = self.create_binary_path("foo/bar/default/crossbench_mock_binary")
    binary = Binary("crossbench_mock_binary", posix=result)
    self.validate_known_binary_posix(result, binary)
    binary = PosixBinary(result)
    self.validate_known_binary_posix(result, binary)

  def validate_known_binary_posix(self, result, binary):
    for platform in self.all_mock_platforms():
      if not platform.is_posix:
        continue
      self.assertEqual(binary.resolve(platform), result)
      self.assertEqual(binary.resolve_cached(platform), result)

    for platform in self.all_mock_platforms():
      if platform.is_posix:
        continue
      self.assertIsNone(binary.platform_path(platform))
      with self.assertRaises(BinaryNotFoundError):
        binary.resolve(platform)
      with self.assertRaises(BinaryNotFoundError):
        binary.resolve_cached(platform)

  def test_known_binary_win(self):
    result = self.create_binary_path(
        "foo/bar/default/crossbench_mock_binary.exe")
    binary = Binary("crossbench_mock_binary", win=result)
    self.validate_known_binary_win(result, binary)
    binary = WinBinary(result)
    self.validate_known_binary_win(result, binary)

  def validate_known_binary_win(self, result, binary):
    platform = WinMockPlatform()
    self.assertEqual(binary.resolve(platform), result)
    self.assertEqual(binary.resolve_cached(platform), result)

    for platform in self.all_mock_platforms():
      if platform.is_win:
        continue
      self.assertIsNone(binary.platform_path(platform))
      with self.assertRaises(BinaryNotFoundError):
        binary.resolve(platform)
      with self.assertRaises(BinaryNotFoundError):
        binary.resolve_cached(platform)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
