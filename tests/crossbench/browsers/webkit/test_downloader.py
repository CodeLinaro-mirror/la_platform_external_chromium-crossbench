# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc

from crossbench import path as pth
from crossbench.browsers.webkit.downloader import (
  WebKitDownloader,
  WebKitDownloaderMacOS,
)
from crossbench.plt.arch import MachineArch
from tests import test_helper
from tests.crossbench.browsers.downloader_helper import (
  AbstractDownloaderTestCase,
)


class AbstractWebKitDownloaderTestCase(
  AbstractDownloaderTestCase, metaclass=abc.ABCMeta
):
  __test__ = False

  def test_name(self):
    self.assertEqual(WebKitDownloader.name(), "WebKit-Nightly")

  def test_wrong_versions(self) -> None:
    with self.assertRaises(ValueError):
      WebKitDownloader.load("", self.platform)
    with self.assertRaises(ValueError):
      WebKitDownloader.load("M", self.platform)
    with self.assertRaises(ValueError):
      WebKitDownloader.load("Webkit Dev", self.platform)
    with self.assertRaises(ValueError):
      WebKitDownloader.load("Safari", self.platform)

  def test_empty_path(self) -> None:
    with self.assertRaises(ValueError):
      WebKitDownloader.load(pth.LocalPath("custom"), self.platform)


class BasicWebKitDownloaderTestCaseLinux(AbstractWebKitDownloaderTestCase):
  __test__ = True

  OS_NAME = "linux"
  MACHINE = MachineArch.X64

  # TODO: Add linux support


class BasicWebKitDownloaderTestCaseMacOS(AbstractWebKitDownloaderTestCase):
  __test__ = True

  OS_NAME = "macos"
  MACHINE = MachineArch.ARM_64

  def test_is_valid_archive(self) -> None:
    self._assert_valid_archive(
      "archive.zip", WebKitDownloader, WebKitDownloaderMacOS
    )

  def test_is_valid_strings(self) -> None:
    self.assertFalse(WebKitDownloader.is_valid("", self.platform))
    self.assertFalse(WebKitDownloader.is_valid("webkit-nightly", self.platform))
    self.assertTrue(
      WebKitDownloader.is_valid("webkit-nightly-12356", self.platform)
    )
    self.assertTrue(
      WebKitDownloader.is_valid("webkit-nightly 12356", self.platform)
    )
    self.assertTrue(
      WebKitDownloader.is_valid("webkit nightly 12356", self.platform)
    )
    self.assertTrue(
      WebKitDownloader.is_valid("webkit-nightly-12356@main", self.platform)
    )
    self.assertTrue(
      WebKitDownloader.is_valid("webkit-nightly 12356@main", self.platform)
    )
    self.assertTrue(
      WebKitDownloader.is_valid("webkit nightly 12356@main", self.platform)
    )

    self.assertTrue(WebKitDownloader.is_valid("webkit-12356", self.platform))
    self.assertTrue(WebKitDownloader.is_valid("webkit 12356", self.platform))
    self.assertTrue(
      WebKitDownloader.is_valid("webkit-12356@main", self.platform)
    )
    self.assertTrue(
      WebKitDownloader.is_valid("webkit 12356@main", self.platform)
    )


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
