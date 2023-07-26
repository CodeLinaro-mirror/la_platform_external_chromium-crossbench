# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
import shutil
import sys
import unittest
from typing import Union

import pytest

from crossbench import compat
from crossbench.browsers.chrome import ChromeWebDriver
from crossbench.browsers.chrome.downloader import ChromeDownloader
from crossbench.browsers.chromium.chromium_webdriver import (ChromeDriverFinder,
                                                             DriverNotFoundError
                                                            )
from crossbench.platform import PLATFORM
from tests.end2end.helper import End2EndTestCase


class ChromeDownloaderTestCase(End2EndTestCase):
  __test__ = True

  def setUp(self) -> None:
    super().setUp()
    if not self.platform.which("gsutil"):
      self.skipTest("Missing required 'gsutil', skipping test.")
    self.archive_dir = self.output_dir / "archive"
    self.assertFalse(self.archive_dir.exists())

  def load_and_check_version(self,
                             version_or_archive: Union[str, pathlib.Path],
                             version_str: str,
                             expect_archive: bool = True) -> pathlib.Path:
    app_path: pathlib.Path = ChromeDownloader.load(version_or_archive,
                                                   self.platform,
                                                   self.output_dir)
    self.assertTrue(compat.is_relative_to(app_path, self.output_dir))
    self.assertTrue(self.archive_dir.exists())
    self.assertTrue(app_path.exists())
    if self.platform.is_macos:
      self.assertSetEqual(
          set(self.output_dir.iterdir()), {app_path, self.archive_dir})
    self.assertIn(version_str, self.platform.app_version(app_path))
    archives = list(self.archive_dir.iterdir())
    if expect_archive:
      self.assertEqual(len(archives), 1)
    else:
      self.assertListEqual(archives, [])
    self.assertTrue(app_path.exists())
    chrome = ChromeWebDriver("test-chrome", app_path, platform=self.platform)
    self.assertIn(version_str, chrome.version)
    self.load_and_check_chromedriver(chrome)
    return app_path

  def load_and_check_chromedriver(self, chrome: ChromeWebDriver) -> None:
    driver_dir = self.output_dir / "chromedriver-binaries"
    driver_dir.mkdir()
    finder = ChromeDriverFinder(chrome, cache_dir=driver_dir)
    self.assertListEqual(list(driver_dir.iterdir()), [])
    with self.assertRaises(DriverNotFoundError):
      finder.find_local_build()
    driver_path: pathlib.Path = finder.download()
    self.assertListEqual(list(driver_dir.iterdir()), [driver_path])
    self.assertTrue(driver_path.is_file())
    # Downloading again should use the cache-version
    driver_path: pathlib.Path = finder.download()
    self.assertListEqual(list(driver_dir.iterdir()), [driver_path])
    self.assertTrue(driver_path.is_file())
    # Restore output dir state.
    driver_path.unlink()
    driver_dir.rmdir()

  def test_download_major_version(self) -> None:
    self.assertListEqual(list(self.output_dir.iterdir()), [])
    self.load_and_check_version("chrome-M111", "111", expect_archive=False)

    # Re-downloading should reuse the extracted app.
    app_path = self.load_and_check_version(
        "chrome-M111", "111", expect_archive=False)

    # Delete the extracted app and reload, can't reuse the cached archive since
    # we're requesting only a milestone that could have been updated
    # in the meantime.
    if self.platform.is_macos:
      shutil.rmtree(app_path)
    else:
      shutil.rmtree(self.output_dir / "M111")
    self.assertFalse(app_path.exists())
    self.load_and_check_version("chrome-M111", "111", expect_archive=False)

  def test_download_major_version_chrome_for_testing(self) -> None:
    # Post M114 we're relying on the new chrome-for-testing download
    self.assertListEqual(list(self.output_dir.iterdir()), [])
    self.load_and_check_version("chrome-M115", "115", expect_archive=False)

    # Re-downloading should reuse the extracted app.
    app_path = self.load_and_check_version(
        "chrome-M115", "115", expect_archive=False)

    # Delete the extracted app and reload, can't reuse the cached archive since
    # we're requesting only a milestone that could have been updated
    # in the meantime.
    if self.platform.is_macos:
      shutil.rmtree(app_path)
    else:
      shutil.rmtree(self.output_dir / "M115")
    self.assertFalse(app_path.exists())
    self.load_and_check_version("chrome-M115", "115", expect_archive=False)

  def test_download_specific_version(self) -> None:
    self.assertListEqual(list(self.output_dir.iterdir()), [])
    version_str = "111.0.5563.110"
    self.load_and_check_version(f"chrome-{version_str}", version_str)

    # Re-downloading should work as well and hit the extracted app.
    app_path = self.load_and_check_version(f"chrome-{version_str}", version_str)

    # Delete the extracted app and reload, should reuse the cached archive.
    if self.platform.is_macos:
      shutil.rmtree(app_path)
    else:
      shutil.rmtree(self.output_dir / version_str)
    self.assertFalse(app_path.exists())
    app_path = self.load_and_check_version(f"chrome-{version_str}", version_str)

    # Delete app and install from archive.
    if self.platform.is_macos:
      shutil.rmtree(app_path)
    else:
      shutil.rmtree(self.output_dir / version_str)
    self.assertFalse(app_path.exists())
    archives = list(self.archive_dir.iterdir())
    self.assertEqual(len(archives), 1)
    archive = archives[0]
    app_path = self.load_and_check_version(archive, version_str)
    self.assertListEqual(list(self.archive_dir.iterdir()), [archive])

  @unittest.skipIf(PLATFORM.is_macos and PLATFORM.is_arm64,
                   "Old versions only supported on intel machines.")
  def test_download_old_major_version(self) -> None:
    self.assertListEqual(list(self.output_dir.iterdir()), [])
    self.load_and_check_version("chrome-M68", "68", expect_archive=False)


if __name__ == "__main__":
  sys.exit(pytest.main([__file__]))
