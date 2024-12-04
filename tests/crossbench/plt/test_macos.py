# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import plistlib

from pyfakefs.fake_filesystem import OSType

from crossbench import path as pth
from tests import test_helper
from tests.crossbench.mock_helper import MacOsMockPlatform
from tests.crossbench.plt.helper import BasePosixMockPlatformTestCase


class MacOsMockPlatformTestCase(BasePosixMockPlatformTestCase):
  __test__ = True

  def setUp(self) -> None:
    super().setUp()
    self.fs.os = OSType.MACOS

  def mock_platform_setup(self) -> None:
    self.mock_platform = MacOsMockPlatform()
    self.platform = self.mock_platform

  def test_name(self):
    self.assertEqual(self.platform.name, "mock.macos")

  def test_is_macos(self):
    self.assertTrue(self.platform.is_macos)

  def test_app_version_non_existing(self):
    app_path = pth.AnyPath("/Applications/Google Chrome.app")
    self.assertFalse(self.platform.exists(app_path))
    with self.assertRaisesRegex(ValueError, "not exist"):
      self.platform.app_version(app_path)

  def test_app_version_binary(self):
    app_path = pth.AnyPath("/opt/homebrew/bin/brew")
    self.fs.create_file(app_path, st_size=100)
    self.expect_sh(app_path, "--version", result="111.22.3")
    self.assertEqual(self.platform.app_version(app_path), "111.22.3")

  def test_app_version(self):
    app_path = pth.LocalPath("/Applications/Google Chrome.app")
    with self.assertRaisesRegex(ValueError, str(app_path)):
      self.platform.app_version(app_path)
    app_path.mkdir(parents=True)
    with self.assertRaisesRegex(ValueError, str(app_path)):
      self.platform.app_version(app_path)

    binary_path = app_path / "Contents/MacOS/Google Chrome"
    binary_path.parent.mkdir(parents=True)
    with self.assertRaisesRegex(ValueError, "Info.plist"):
      self.platform.app_version(app_path)

    info_plist = app_path / "Contents/Info.plist"
    self.fs.create_file(info_plist)
    with self.assertRaisesRegex(ValueError, "Invalid file"):
      self.platform.app_version(app_path)

    with info_plist.open("wb") as f:
      plistlib.dump({}, f)
    with self.assertRaisesRegex(ValueError, str(app_path)):
      self.platform.app_version(app_path)

    with info_plist.open("wb") as f:
      plistlib.dump(
          {
              "CFBundleShortVersionString": "129.9.6668.103",
              "CFBundleDisplayName": "Google Chrome",
          }, f)
    self.assertEqual(
        self.platform.app_version(app_path), "Google Chrome 129.9.6668.103")

    with info_plist.open("wb") as f:
      plistlib.dump(
          {
              "CFBundleShortVersionString": "129.9.6668.103",
              # CFBundleDisplayName is missing but CFBundleName is there.
              "CFBundleName": "Google Chrome",
          }, f)
    self.assertEqual(
        self.platform.app_version(app_path), "Google Chrome 129.9.6668.103")

  def test_app_version_binary_inside_app(self):
    binary_path = pth.LocalPath("/Applications/Safari Technology Preview.app/"
                                "Contents/MacOS/safaridriver")
    self.fs.create_file(binary_path, st_size=100)
    self.expect_sh(binary_path, "--version", result="(Release 203, 19620.1.6)")
    self.assertEqual(
        self.platform.app_version(binary_path), "(Release 203, 19620.1.6)")

  def test_search_binary(self):
    app_path = pth.LocalPath("/Applications/Google Chrome.app")
    self.assertIsNone(self.platform.search_binary(app_path))
    binary_path = app_path / "Contents/MacOS/Google Chrome"
    self.fs.create_file(binary_path, st_size=100)
    self.assertEqual(self.platform.search_binary(app_path), binary_path)

  def test_search_binary_custom_bundle_executable(self):
    app_path = pth.LocalPath("/Applications/Google Chrome.app")
    self.assertIsNone(self.platform.search_binary(app_path))
    binary_path = app_path / "Contents/MacOS/Chrome"
    binary_path.parent.mkdir(parents=True)
    with self.assertRaisesRegex(ValueError, "Info.plist"):
      self.platform.search_binary(app_path)

    info_plist = app_path / "Contents/Info.plist"
    self.fs.create_file(info_plist)
    with self.assertRaisesRegex(ValueError, "Invalid file"):
      self.platform.search_binary(app_path)

    with info_plist.open("wb") as f:
      plistlib.dump({}, f)
    with self.assertRaisesRegex(ValueError, str(app_path)):
      self.platform.search_binary(app_path)

    with info_plist.open("wb") as f:
      plistlib.dump({"CFBundleExecutable": str(binary_path)}, f)
    with self.assertRaisesRegex(ValueError, str(app_path)):
      self.platform.search_binary(app_path)

    self.fs.create_file(binary_path, st_size=100)
    # Single binary is always resolved directly
    self.assertEqual(self.platform.search_binary(app_path), binary_path)

    # Adding another binary will still resolve to CFBundleExecutable
    self.fs.create_file(binary_path.parent / "Other", st_size=100)
    self.assertEqual(self.platform.search_binary(app_path), binary_path)

  def test_search_binary_single(self):
    app_path = pth.LocalPath("/Applications/Custom.app")
    binary_path = app_path / "Contents/MacOS/CustomA"
    self.fs.create_file(binary_path, st_size=100)
    self.assertEqual(self.platform.search_binary(app_path), binary_path)

  def test_search_binary_multiple_binaries(self):
    app_path = pth.LocalPath("/Applications/Custom.app")
    self.fs.create_file(app_path / "Contents/MacOS/CustomA", st_size=100)
    self.fs.create_file(app_path / "Contents/MacOS/CustomB", st_size=100)
    info_plist = app_path / "Contents/Info.plist"
    with info_plist.open("wb") as f:
      plistlib.dump({}, f)
    with self.assertRaisesRegex(ValueError, "binaries"):
      self.platform.search_binary(app_path)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
