# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import argparse

from typing_extensions import override

from crossbench import path as pth
from crossbench.browsers.chrome.version import ChromeVersion
from crossbench.browsers.chrome.webdriver import ChromeWebDriver, \
    LocalChromeWebDriverAndroid
from crossbench.browsers.settings import Settings
from crossbench.flags.chrome import ChromeFlags
from tests import test_helper
from tests.crossbench import mock_browser
from tests.crossbench.base import BaseCrossbenchTestCase


class ChromeWebDriverForTesting(ChromeWebDriver):

  @override
  def _extract_version(self) -> ChromeVersion:
    return ChromeVersion.parse(mock_browser.MockChromeStable.VERSION)


class ChromeWebdriverTestCase(BaseCrossbenchTestCase):

  def test_conflicting_finch_flags(self) -> None:
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      ChromeWebDriverForTesting(
          label="browser-label",
          path=mock_browser.MockChromeStable.mock_app_path(),
          settings=Settings(
              js_flags=[],
              flags=[
                  "--disable-field-trial-config", "--enable-field-trial-config"
              ],
              platform=self.platform))
    msg = str(cm.exception)
    self.assertIn("--enable-field-trial-config", msg)
    self.assertIn("--disable-field-trial-config", msg)

  def test_auto_disabling_field_trials(self):
    browser = ChromeWebDriverForTesting(
        label="browser-label",
        path=mock_browser.MockChromeStable.mock_app_path(),
        settings=Settings(platform=self.platform))
    self.assertIn("--disable-field-trial-config", browser.flags)

    browser_field_trial = ChromeWebDriverForTesting(
        label="browser-label",
        path=mock_browser.MockChromeStable.mock_app_path(),
        settings=Settings(
            flags=["--force-fieldtrials"], platform=self.platform))
    self.assertIn("--force-fieldtrials", browser_field_trial.flags)
    self.assertNotIn("--disable-field-trial-config", browser_field_trial.flags)

  def test_auto_disabling_field_trials_all(self):
    for field_trial_flag in ChromeFlags.FIELD_TRIAL_ENABLE_FLAGS:
      if field_trial_flag == "--enable-benchmarking":
        continue
      browser = ChromeWebDriverForTesting(
          label="browser-label",
          path=mock_browser.MockChromeStable.mock_app_path(),
          settings=Settings(flags=[field_trial_flag], platform=self.platform))
      flags: ChromeFlags = browser.flags
      self.assertIn(field_trial_flag, flags)
      self.assertFalse(flags.field_trial_disable_flags)

  def test_is_local_build_mock_browser(self):
    self.assertTrue(self.browsers)
    for browser in self.browsers:
      self.assertFalse(browser.is_local_build)


class LocalChromeWebDriverAndroidTestCase(BaseCrossbenchTestCase):

  def test_is_apk_helper(self):
    self.assertTrue(
        LocalChromeWebDriverAndroid.is_apk_helper(
            pth.AnyPath("/home/user/Documents/chrome/src/"
                        "out/arm64.apk/bin/chrome_public_apk")))
    self.assertFalse(LocalChromeWebDriverAndroid.is_apk_helper(None))
    self.assertFalse(
        LocalChromeWebDriverAndroid.is_apk_helper(
            pth.AnyPath("org.chromium.chrome")))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
