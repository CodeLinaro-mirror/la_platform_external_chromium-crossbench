# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase

from crossbench import path as pth
from crossbench.browsers.chromium.webdriver import \
    LocalChromiumWebDriverAndroid


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


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
