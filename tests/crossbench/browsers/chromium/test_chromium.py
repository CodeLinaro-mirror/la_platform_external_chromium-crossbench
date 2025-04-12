# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
from unittest import mock

from crossbench import path as pth
from crossbench.browsers.chromium.webdriver import (
    ChromiumWebDriver, LocalChromiumWebDriverAndroid)
from crossbench.browsers.chromium_based import helper
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


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
