# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc

from crossbench import path as pth
from crossbench.browsers.firefox.downloader import FirefoxDownloader, \
    FirefoxDownloaderLinux, FirefoxDownloaderMacOS, FirefoxDownloaderWin
from crossbench.plt.arch import MachineArch
from tests import test_helper
from tests.crossbench.browsers.downloader_helper import \
    AbstractDownloaderTestCase


class AbstractFirefoxDownloaderTestCase(
    AbstractDownloaderTestCase, metaclass=abc.ABCMeta):
  __test__ = False

  def test_name(self) -> None:
    self.assertEqual(FirefoxDownloader.name(), "Firefox")

  def test_wrong_versions(self) -> None:
    with self.assertRaises(ValueError):
      FirefoxDownloader.load("", self.platform)
    with self.assertRaises(ValueError):
      FirefoxDownloader.load("ff", self.platform)
    with self.assertRaises(ValueError):
      FirefoxDownloader.load("firefox", self.platform)
    with self.assertRaises(ValueError):
      FirefoxDownloader.load("124-0.2", self.platform)
    with self.assertRaises(ValueError):
      FirefoxDownloader.load("124-0.2", self.platform)
    with self.assertRaises(ValueError):
      FirefoxDownloader.load("124.0ab2", self.platform)
    with self.assertRaises(ValueError):
      FirefoxDownloader.load("124.0.2.3.5", self.platform)

  def test_valid_versions_stable(self):
    self.assertFalse(FirefoxDownloader.is_valid("124.0.2", self.platform))
    self.assertTrue(FirefoxDownloader.is_valid("ff-124.0.2", self.platform))
    self.assertTrue(
        FirefoxDownloader.is_valid("firefox-124.0.2", self.platform))

  def test_valid_versions_beta(self):
    self.assertTrue(FirefoxDownloader.is_valid("104.0b9", self.platform))
    self.assertTrue(FirefoxDownloader.is_valid("ff-104.0b9", self.platform))
    self.assertTrue(
        FirefoxDownloader.is_valid("firefox-104.0b9", self.platform))

    self.assertFalse(FirefoxDownloader.is_valid("104.0ab9", self.platform))
    self.assertFalse(FirefoxDownloader.is_valid("ff-104.0ab9", self.platform))
    self.assertFalse(
        FirefoxDownloader.is_valid("firefox-104.0ab9", self.platform))

  def test_valid_versions_esr(self):
    self.assertTrue(FirefoxDownloader.is_valid("115.0.3esr", self.platform))
    self.assertTrue(FirefoxDownloader.is_valid("ff-115.0.3esr", self.platform))
    self.assertTrue(
        FirefoxDownloader.is_valid("firefox-115.0.3esr", self.platform))

    self.assertFalse(FirefoxDownloader.is_valid("115.0a3esr", self.platform))
    self.assertFalse(FirefoxDownloader.is_valid("ff-115.0a3esr", self.platform))
    self.assertFalse(
        FirefoxDownloader.is_valid("firefox-115.0a3esr", self.platform))

  def test_empty_path(self) -> None:
    with self.assertRaises(ValueError):
      FirefoxDownloader.load(pth.LocalPath("custom"), self.platform)


class BasicFirefoxDownloaderLinuxTestCase(AbstractFirefoxDownloaderTestCase):
  __test__ = True

  OS_NAME = "linux"
  MACHINE = MachineArch.X64

  def test_is_valid_archive(self) -> None:
    self._assert_valid_archive("archive.tar.bz2", FirefoxDownloader,
                               FirefoxDownloaderLinux,
                               (FirefoxDownloaderMacOS, FirefoxDownloaderWin))


class BasicFirefoxDownloaderMacOSTestCase(AbstractFirefoxDownloaderTestCase):
  __test__ = True

  OS_NAME = "macos"
  MACHINE = MachineArch.ARM_64

  def test_is_valid_archive(self) -> None:
    self._assert_valid_archive("archive.dmg", FirefoxDownloader,
                               FirefoxDownloaderMacOS,
                               (FirefoxDownloaderLinux, FirefoxDownloaderWin))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
