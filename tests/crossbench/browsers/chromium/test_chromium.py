# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import datetime as dt
import pathlib
import re
import unittest
from unittest import mock

from crossbench import path as pth
from crossbench.browsers.chromium.base import ChromiumBaseMixin
from crossbench.browsers.chromium.webdriver import ChromiumWebDriver, \
    LocalChromiumWebDriverAndroid
from crossbench.browsers.chromium_based import helper
from crossbench.browsers.chromium_based.webdriver import ChromiumBasedWebDriver
from crossbench.browsers.settings import Settings
from tests import test_helper
from tests.crossbench import mock_browser
from tests.crossbench.base import BaseCrossbenchTestCase


class LocalChromeWebDriverAndroidTestCase(BaseCrossbenchTestCase):

  def test_is_apk_helper(self):
    self.assertTrue(
        LocalChromiumWebDriverAndroid.is_apk_helper(
            pth.AnyPath("/home/user/Documents/chrome/src/"
                        "out/arm64.apk/bin/chrome_public_apk")))
    self.assertFalse(LocalChromiumWebDriverAndroid.is_apk_helper(None))
    self.assertFalse(
        LocalChromiumWebDriverAndroid.is_apk_helper(
            pth.AnyPath("org.chromium.chrome")))

  def test_is_local_build_mock_browser(self):
    self.assertTrue(self.browsers)
    for browser in self.browsers:
      self.assertFalse(browser.is_local_build)

  def test_is_local_build(self):
    build_dir = pathlib.Path("/home/testuser/chrome/src/out/release")
    path = build_dir / mock_browser.MockChromium.mock_app_binary()
    self.fs.create_file(path, st_size=1000)
    self.assertFalse(helper.is_in_build_dir(path, self.platform))

    version_str = mock_browser.MockChromium.VERSION
    with mock.patch.object(
        self.platform, "app_version", return_value=version_str):
      # Missing args.gn => cannot detect local build:
      browser = ChromiumWebDriver(
          "local", path=path, settings=Settings(platform=self.platform))
      self.assertFalse(browser.is_local_build)
      self.assertEqual(browser.version.version_str, version_str)

      self.fs.create_file(build_dir / "args.gn")
      self.assertTrue(helper.is_in_build_dir(path, self.platform))
      browser = ChromiumWebDriver(
          "local", path=path, settings=Settings(platform=self.platform))
      self.assertTrue(browser.is_local_build)
      self.assertFalse(browser.version.has_channel)
      self.assertEqual(browser.version.version_str, version_str)


class MockChromiumBasedWebDriver(ChromiumBaseMixin, ChromiumBasedWebDriver):

  def __init__(self, label, driver) -> None:
    mock_platform = mock.MagicMock(name="Mock Platform")
    mock_platform.app_version.side_effect = [mock_browser.MockChromium.VERSION]
    self._private_driver = driver
    super().__init__(
        label=label, path=None, settings=Settings(platform=mock_platform))

  def _create_driver(self, options, service):
    raise RuntimeError("start() should not be called")


class ChromiumBasedWebDriverTestCase(unittest.TestCase):

  def _make_tab_switch_mocks(self, handles, current):
    mock_driver = mock.MagicMock(name="Mock Driver")
    browser = MockChromiumBasedWebDriver("test-driver", mock_driver)

    def switch_to_window(handle):
      mock_driver.current_window_handle = handle
      mock_driver.title = handle
      mock_driver.current_url = f"https://{handle}.com"

    switch_to_window(current)

    mock_driver.switch_to.window.side_effect = switch_to_window
    mock_driver.window_handles = handles
    return (browser, mock_driver)

  def test_switch_tab_title(self):
    browser, mock_driver = self._make_tab_switch_mocks(["a", "b", "c"], "b")

    browser.switch_tab(title=re.compile("^c$"), timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "c")
    self.assertEqual(mock_driver.current_url, "https://c.com")

    browser.switch_tab(title=re.compile("^a$"), timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "a")
    self.assertEqual(mock_driver.current_url, "https://a.com")

    browser.switch_tab(title=re.compile("^b$"), timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "b")
    self.assertEqual(mock_driver.current_url, "https://b.com")

  def test_switch_tab_url(self):
    browser, mock_driver = self._make_tab_switch_mocks(["1", "2", "3"], "2")

    browser.switch_tab(url=re.compile(".*3.*"), timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "3")
    self.assertEqual(mock_driver.current_url, "https://3.com")

    browser.switch_tab(url=re.compile(".*1.*"), timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "1")
    self.assertEqual(mock_driver.current_url, "https://1.com")

    browser.switch_tab(url=re.compile(".*2.*"), timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "2")
    self.assertEqual(mock_driver.current_url, "https://2.com")

  def test_switch_tab_index(self):
    browser, mock_driver = self._make_tab_switch_mocks(["1", "2", "3"], "2")

    # Switch to current tab.
    browser.switch_tab(tab_index=1, timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "2")
    self.assertEqual(mock_driver.current_url, "https://2.com")

    # Switch to first tab.
    browser.switch_tab(tab_index=0, timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "1")
    self.assertEqual(mock_driver.current_url, "https://1.com")

    # Overflow tab_index.
    with self.assertRaises(IndexError):
      browser.switch_tab(tab_index=3, timeout=dt.timedelta(seconds=5))

    # Switch to last tab using negative tab_index.
    browser.switch_tab(tab_index=-1, timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "3")
    self.assertEqual(mock_driver.current_url, "https://3.com")

    # Underflow tab_index.
    with self.assertRaises(IndexError):
      browser.switch_tab(tab_index=-4, timeout=dt.timedelta(seconds=5))

  def test_switch_relative_tab_index(self):
    browser, mock_driver = self._make_tab_switch_mocks(["1", "2", "3"], "2")

    # Switch to current tab
    browser.switch_tab(relative_tab_index=0, timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "2")
    self.assertEqual(mock_driver.current_url, "https://2.com")

    # Next tab.
    browser.switch_tab(relative_tab_index=1, timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "3")
    self.assertEqual(mock_driver.current_url, "https://3.com")

    # Wrap positive.
    browser.switch_tab(relative_tab_index=1, timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "1")
    self.assertEqual(mock_driver.current_url, "https://1.com")

    # Wrap negative
    browser.switch_tab(relative_tab_index=-1, timeout=dt.timedelta(seconds=5))
    self.assertEqual(mock_driver.title, "3")
    self.assertEqual(mock_driver.current_url, "https://3.com")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
