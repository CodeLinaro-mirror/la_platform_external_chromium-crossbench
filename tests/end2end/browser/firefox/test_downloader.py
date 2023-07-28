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
from crossbench.browsers.firefox import FirefoxDownloader, FirefoxWebDriver
from crossbench.browsers.firefox.firefox_webdriver import FirefoxDriverFinder
from crossbench.platform import PLATFORM
from tests.end2end.helper import End2EndTestCase


@unittest.skipIf(not PLATFORM.is_macos, "Only supported on macOS")
class FirefoxDownloaderTestCase(End2EndTestCase):
  __test__ = True

  def setUp(self) -> None:
    super().setUp()
    self.archive_dir = self.output_dir / "archive"
    self.assertFalse(self.archive_dir.exists())

  def load_and_check_version(self,
                             version_or_archive: Union[str, pathlib.Path],
                             version_str: str,
                             expect_archive: bool = True) -> pathlib.Path:
    app_path: pathlib.Path = FirefoxDownloader.load(version_or_archive,
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
    browser = FirefoxWebDriver("test-browser", app_path, platform=self.platform)
    # TODO: fix using dedicated Version object
    base_version_str = version_str.split("b")[0]
    self.assertIn(base_version_str, browser.version)
    self.load_and_check_webdriver(browser)
    return app_path

  def load_and_check_webdriver(self, browser: FirefoxWebDriver) -> None:
    driver_dir = self.output_dir / "chromedriver-binaries"
    driver_dir.mkdir()
    finder = FirefoxDriverFinder(browser, cache_dir=driver_dir)
    self.assertListEqual(list(driver_dir.iterdir()), [])
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

  def test_download_specific_version(self) -> None:
    self.assertListEqual(list(self.output_dir.iterdir()), [])
    version_str = "106.0.4"
    self.load_and_check_version(f"firefox-{version_str}", version_str)

    # Re-downloading should work as well and hit the extracted app.
    app_path = self.load_and_check_version(f"firefox-{version_str}",
                                           version_str)

    # Delete the extracted app and reload, should reuse the cached archive.
    if self.platform.is_macos:
      shutil.rmtree(app_path)
    else:
      shutil.rmtree(self.output_dir / version_str)
    self.assertFalse(app_path.exists())
    app_path = self.load_and_check_version(f"firefox-{version_str}",
                                           version_str)
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

  def test_download_specific_beta_version(self) -> None:
    self.assertListEqual(list(self.output_dir.iterdir()), [])
    version_str = "115.0b4"
    self.load_and_check_version(f"firefox-{version_str}", version_str)

    # Re-downloading should work as well and hit the extracted app.
    app_path = self.load_and_check_version(f"firefox-{version_str}",
                                           version_str)

    # Delete the extracted app and reload, should reuse the cached archive.
    if self.platform.is_macos:
      shutil.rmtree(app_path)
    else:
      shutil.rmtree(self.output_dir / version_str)
    self.assertFalse(app_path.exists())
    app_path = self.load_and_check_version(f"firefox-{version_str}",
                                           version_str)

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


if __name__ == "__main__":
  sys.exit(pytest.main([__file__]))
