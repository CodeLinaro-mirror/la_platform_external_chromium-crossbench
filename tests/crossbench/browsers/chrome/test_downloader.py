# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
from unittest import mock

from crossbench import path as pth
from crossbench.browsers.chrome.downloader import ChromeDownloader, \
    ChromeDownloaderAndroid, ChromeDownloaderLinux, ChromeDownloaderMacOS, \
    ChromeDownloaderWin
from crossbench.plt.arch import MachineArch
from tests import test_helper
from tests.crossbench.browsers.downloader_helper import \
    AbstractDownloaderTestCase


class AbstractChromeDownloaderTestCase(
    AbstractDownloaderTestCase, metaclass=abc.ABCMeta):
  __test__ = False

  def test_name(self):
    self.assertEqual(ChromeDownloader.name(), "Chrome")

  def test_wrong_versions(self) -> None:
    with self.assertRaises(ValueError):
      ChromeDownloader.load("", self.platform)
    with self.assertRaises(ValueError):
      ChromeDownloader.load("M", self.platform)
    with self.assertRaises(ValueError):
      ChromeDownloader.load("M-100", self.platform)
    with self.assertRaises(ValueError):
      ChromeDownloader.load("M100.1.2.3.4.5", self.platform)
    with self.assertRaises(ValueError):
      ChromeDownloader.load("100.1.2.3.4.5", self.platform)

  def test_empty_path(self) -> None:
    with self.assertRaises(ValueError):
      ChromeDownloader.load(pth.LocalPath("custom"), self.platform)

  def test_load_valid_non_googler(self) -> None:
    self.platform.search_app = lambda app_or_bin: None
    self.platform.host_platform.check_gcs_file_exists = mock.Mock(
        side_effect=PermissionError("Forbidden"))
    with self.assertRaises(ValueError):
      ChromeDownloader.load("chrome-111.0.5563.110", self.platform)

  def test_is_valid_strings(self) -> None:
    self.assertFalse(ChromeDownloader.is_valid("", self.platform))
    self.assertFalse(ChromeDownloader.is_valid("mM45", self.platform))
    self.assertFalse(ChromeDownloader.is_valid("M4", self.platform))
    self.assertFalse(ChromeDownloader.is_valid("M1234", self.platform))
    self.assertFalse(ChromeDownloader.is_valid("M123.4", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("M123 ", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("M12 ", self.platform))
    self.assertFalse(ChromeDownloader.is_valid("145", self.platform))
    self.assertFalse(ChromeDownloader.is_valid("45", self.platform))
    self.assertFalse(ChromeDownloader.is_valid("i145", self.platform))
    self.assertFalse(ChromeDownloader.is_valid("i45", self.platform))
    self.assertFalse(ChromeDownloader.is_valid("chr-i145", self.platform))
    self.assertFalse(ChromeDownloader.is_valid("chr-i45", self.platform))

    self.assertTrue(ChromeDownloader.is_valid("M45", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("M45 stable", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("M45-canary", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("m45", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chrome-m45", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chrome-m45-dev", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chrome-45", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chr-m45", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chr-45", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chr-45-stable", self.platform))

    self.assertTrue(ChromeDownloader.is_valid("M100", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("M100 stable", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("M100-stable", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("m100", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chrome-m100", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chrome-m100-dev", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chrome-100", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chr-m100", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chr-100", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("chr-100-stable", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("Google Chrome m100", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("Google Chrome 100", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("Google Chrome extended", self.platform))

    self.assertFalse(
        ChromeDownloader.is_valid("M100.1.2.123.9999", self.platform))
    self.assertTrue(ChromeDownloader.is_valid("M111.0.5563.110", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("M111.0.5563.110 stable", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("Google Chrome M111.0.5563.110",
                                  self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("Google Chrome Canary M111.0.5563.110",
                                  self.platform))
    self.assertFalse(ChromeDownloader.is_valid("111.0.5563.110", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("Google Chrome 111.0.5563.110",
                                  self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("Google Chrome 111.0.5563.110 canary",
                                  self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("Google Chrome Canary111.0.5563.110",
                                  self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("chrome-11.0.5563.110", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("chrome-M11.0.5563.110", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("chr-11.0.5563.110", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("chrome-111.0.5563.110", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("chr-111.0.5563.110", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("chr-111.0.5563.110-canary", self.platform))

  def test_is_valid_strings_latest(self):
    self.assertTrue(
        ChromeDownloader.is_valid("chrome latest stable", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("chrome latest canary", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("chrome-latest-stable", self.platform))
    self.assertTrue(
        ChromeDownloader.is_valid("chrome-latest-dev", self.platform))

  def test_is_valid_path(self) -> None:
    self.assertFalse(
        ChromeDownloader.is_valid(pth.LocalPath("custom"), self.platform))
    path = pth.LocalPath("download/archive.foo")
    self.fs.create_file(path)
    self.assertFalse(ChromeDownloader.is_valid(path, self.platform))


class BasicChromeDownloaderTestCaseLinux(AbstractChromeDownloaderTestCase):
  __test__ = True
  OS_NAME = "linux"
  MACHINE = MachineArch.X64

  def test_is_valid_archive(self) -> None:
    self._assert_valid_archive("archive.rpm", ChromeDownloader,
                               ChromeDownloaderLinux,
                               (ChromeDownloaderMacOS, ChromeDownloaderWin))


class BasicChromeDownloaderTestCaseMacOS(AbstractChromeDownloaderTestCase):
  __test__ = True
  OS_NAME = "macos"
  MACHINE = MachineArch.ARM_64

  def test_is_valid_archive(self) -> None:
    self._assert_valid_archive("archive.dmg", ChromeDownloader,
                               ChromeDownloaderMacOS,
                               (ChromeDownloaderLinux, ChromeDownloaderWin))


class BasicChromeDownloaderTestCaseAndroid(AbstractChromeDownloaderTestCase):
  __test__ = True
  OS_NAME = "android"
  MACHINE = MachineArch.ARM_64

  def test_is_valid_archive(self) -> None:
    self._assert_valid_archive(
        "archive.apks", ChromeDownloader, ChromeDownloaderAndroid,
        (ChromeDownloaderLinux, ChromeDownloaderMacOS, ChromeDownloaderWin))

  def test_download_and_install_chrome_bundle(self) -> None:
    expected_url = (
        "gs://chrome-signed/android-B0urB0N/155.0.8056.0/high-arm_64/"
        "ChromeDev.apks")
    self.platform.host_platform.check_gcs_file_exists = mock.Mock(
        side_effect=lambda url: url == expected_url)

    def fake_download_gcs_file(url: str, dst: pth.LocalPath) -> None:
      self.assertEqual(url, expected_url)
      self.fs.create_file(dst)

    self.platform.host_platform.download_gcs_file = mock.Mock(
        side_effect=fake_download_gcs_file)
    self.platform.app_version = mock.Mock(return_value="155.0.8056.0")
    self._fake_adb_install_package("com.chrome.dev")
    app_path = ChromeDownloader.load("chrome-dev-155.0.8056.0", self.platform)
    self.assertEqual(str(app_path), "com.chrome.dev")
    self.platform.host_platform.download_gcs_file.assert_called_once()
    self.mock_adb.uninstall.assert_called_once_with(
        "com.chrome.dev", missing_ok=True)
    self.mock_adb.install.assert_called_once()

  def test_download_and_install_trichrome_bundle_legacy_milestone(self) -> None:
    expected_apks_url = (
        "gs://chrome-signed/android-B0urB0N/130.0.6723.103/high-arm_64/"
        "TrichromeChromeGoogle6432Stable.apks")
    expected_lib_url = (
        "gs://chrome-signed/android-B0urB0N/130.0.6723.103/high-arm_64/"
        "TrichromeLibraryGoogle6432Stable.apk")
    self.platform.host_platform.check_gcs_file_exists = mock.Mock(
        side_effect=lambda url: url == expected_apks_url)
    downloaded_urls: list[str] = []

    def fake_download_gcs_file(url: str, dst: pth.LocalPath) -> None:
      downloaded_urls.append(url)
      self.fs.create_file(dst)

    self.platform.host_platform.download_gcs_file = mock.Mock(
        side_effect=fake_download_gcs_file)
    self.platform.app_version = mock.Mock(return_value="130.0.6723.103")
    self._fake_adb_install_package("com.android.chrome")
    app_path = ChromeDownloader.load(
        "chrome-stable-130.0.6723.103", self.platform)
    self.assertEqual(str(app_path), "com.android.chrome")
    self.assertEqual(downloaded_urls, [expected_apks_url, expected_lib_url])
    self.mock_adb.uninstall.assert_called_once_with(
        "com.android.chrome", missing_ok=True)
    self.assertEqual(self.mock_adb.install.call_count, 2)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
