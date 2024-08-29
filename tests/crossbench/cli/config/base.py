# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import Type
from unittest import mock

from crossbench import path as pth
from crossbench.cli.config.browser_variants import BrowserVariantsConfig
from tests.crossbench import mock_browser
from tests.crossbench.base import BaseCrossbenchTestCase

XCTRACE_DEVICES_OUTPUT = """
== Devices ==
a-macbookpro3 (00001234-AAAA-BBBB-0000-11AA22BB33DD)
An iPhone (17.1.2) (00001111-11AA22BB33DD)
An iPhone Pro (17.1.1) (00002222-11AA22BB33DD)

== Devices Offline ==
An iPhone Pro Max (17.1.0) (00003333-11AA22BB33DD)

== Simulators ==
iPad (10th generation) (17.0.1) (00001234-AAAA-BBBB-1111-11AA22BB33DD)
iPad (9th generation) Simulator (15.5) (00001234-AAAA-BBBB-2222-11AA22BB33DD
"""
XCTRACE_DEVICES_SINGLE_OUTPUT = """
== Devices ==
a-macbookpro3 (00001234-AAAA-BBBB-0000-11AA22BB33DD)
An iPhone (17.1.2) (00001111-11AA22BB33DD)

== Devices Offline ==
An iPhone Pro (17.1.1) (00002222-11AA22BB33DD)

== Simulators ==
iPad (10th generation) (17.0.1) (00001234-AAAA-BBBB-1111-11AA22BB33DD)
iPad (9th generation) Simulator (15.5) (00001234-AAAA-BBBB-2222-11AA22BB33DD
"""

ADB_DEVICES_SINGLE_OUTPUT = """List of devices attached
emulator-5556 device product:sdk_google_phone_x86_64 model:Android_SDK_built_for_x86_64 device:generic_x86_64"""

ADB_DEVICES_OUTPUT = f"""{ADB_DEVICES_SINGLE_OUTPUT}
emulator-5554 device product:sdk_google_phone_x86 model:Android_SDK_built_for_x86 device:generic_x86
0a388e93      device usb:1-1 product:razor model:Nexus_7 device:flo"""


class BaseConfigTestCase(BaseCrossbenchTestCase):

  def setUp(self) -> None:
    super().setUp()
    adb_patcher = mock.patch(
        "crossbench.plt.android_adb._find_adb_bin",
        return_value=pth.LocalPath("adb"))
    adb_patcher.start()
    self.addCleanup(adb_patcher.stop)

  def mock_chrome_stable(self, browser_cls: Type[mock_browser.MockBrowser]):
    return mock.patch.object(
        BrowserVariantsConfig, "_get_browser_cls", return_value=browser_cls)
