# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import contextlib
import json
from typing import override
from unittest import mock

from pyfakefs.fake_filesystem import OSType

from crossbench import path as pth
from crossbench.action_runner.action.enums import WindowTarget
from crossbench.browsers.attributes import BrowserAttributes
from crossbench.browsers.safari.webdriver import (
  SafariWdaIOS,
  SafariWebdriverIOS,
)
from crossbench.browsers.settings import Settings
from crossbench.cli.config.env import EnvConfig
from crossbench.plt.ios import IOSPlatform
from crossbench.runner.groups.session import BrowserSessionRunGroup
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.browsers.test_webdriver import FakeWebDriver
from tests.crossbench.mock_helper import MacOsMockPlatform
from tests.crossbench.plt.test_ios import DEVICES_SINGLE, SIMULATORS_SAMPLE


class SafariIosBrowserTestCase(CrossbenchFakeFsTestCase):
  __test__ = True

  @override
  def setUp(self) -> None:
    super().setUp()
    self.fs.os = OSType.MACOS
    self.host_platform = self.setup_host_platform()

  def setup_host_platform(self) -> MacOsMockPlatform:
    platform = MacOsMockPlatform()

    @contextlib.contextmanager
    def mock_named_temporary_file(suffix=None, prefix=None, dir=None):
      del suffix, prefix, dir
      yield pth.LocalPath("/devicectl_output.json")

    platform.NamedTemporaryFile = mock_named_temporary_file
    return platform

  def setup_platform(self) -> IOSPlatform:
    if self.fs.exists("/devicectl_output.json"):
      self.fs.remove_object("/devicectl_output.json")
    self.fs.create_file(
      "/devicectl_output.json",
      contents=json.dumps(DEVICES_SINGLE),
    )
    self.host_platform.expect_sh(
      "xcrun",
      "devicectl",
      "list",
      "devices",
      "--json-output=/devicectl_output.json",
      result="",
    )
    self.host_platform.expect_sh(
      "xcrun",
      "simctl",
      "list",
      "devices",
      "booted",
      "--json",
      result=json.dumps(SIMULATORS_SAMPLE),
    )
    return IOSPlatform(self.host_platform, "00001111-11AA22BB33DD")

  def test_attributes(self) -> None:
    platform = self.setup_platform()
    browser = SafariWdaIOS(
      "test-safari",
      platform.path("/Applications/Safari.app"),
      settings=Settings(platform=platform),
    )
    attrs = browser.attributes()
    self.assertTrue(attrs & BrowserAttributes.SAFARI)
    self.assertTrue(attrs & BrowserAttributes.MOBILE)
    self.assertFalse(attrs & BrowserAttributes.WEBDRIVER)

  def test_version_and_paths(self) -> None:
    platform = self.setup_platform()
    browser = SafariWdaIOS(
      "test-safari",
      platform.path("/Applications/Safari.app"),
      settings=Settings(platform=platform),
    )
    self.assertEqual(browser.version.major, 17)
    self.assertIsNone(browser._setup_cache_dir())

  def test_start_and_show_url(self) -> None:
    platform = self.setup_platform()
    mock_network = mock.MagicMock()
    mock_network.is_running = True
    mock_network.extra_flags.return_value = ()
    browser = SafariWdaIOS(
      "test-safari",
      platform.path("/Applications/Safari.app"),
      settings=Settings(platform=platform, network=mock_network),
    )
    mock_wda = mock.MagicMock()
    platform._wda = mock_wda

    session = mock.create_autospec(
      BrowserSessionRunGroup,
      instance=True,
      extra_flags=(),
    )
    session.network = mock.MagicMock()
    session.network.extra_flags.return_value = ()

    browser.start(session)
    mock_wda.terminate_app.assert_called_once_with("com.apple.mobilesafari")
    mock_wda.launch_app.assert_called_once_with(
      "com.apple.mobilesafari", env_vars={}
    )
    self.assertTrue(browser.is_running)

    browser.show_url("https://example.com", WindowTarget.SELF)
    mock_wda.open_url.assert_called_once_with("https://example.com")

    with self.assertRaises(NotImplementedError):
      browser.show_url("https://example.com", WindowTarget.NEW_TAB)

    # about:blank and data: URLs should be ignored.
    mock_wda.open_url.reset_mock()
    browser.show_url("about:blank")
    browser.show_url("data:text/html;charset=utf-8,<html></html>")
    mock_wda.open_url.assert_not_called()

    mock_wda.terminate_app.reset_mock()
    browser.force_quit()
    mock_wda.terminate_app.assert_called_once_with("com.apple.mobilesafari")
    self.assertFalse(browser.is_running)

  def test_js_not_implemented_and_user_agent(self) -> None:
    platform = self.setup_platform()
    browser = SafariWdaIOS(
      "test-safari",
      platform.path("/Applications/Safari.app"),
      settings=Settings(platform=platform),
    )
    self.assertIn("Safari", browser.user_agent())
    with self.assertRaises(NotImplementedError):
      browser.js("return 1;")

  def test_performance_mark_skips_js(self) -> None:
    platform = self.setup_platform()
    browser = SafariWdaIOS(
      "test-safari",
      platform.path("/Applications/Safari.app"),
      settings=Settings(platform=platform),
    )
    # performance_mark should succeed without calling js().
    browser.performance_mark("test-mark")

  def test_manual_mode_does_not_use_wda(self) -> None:
    platform = self.setup_platform()
    mock_network = mock.MagicMock()
    mock_network.is_running = True
    mock_network.extra_flags.return_value = ()
    browser = SafariWdaIOS(
      "test-safari",
      platform.path("/Applications/Safari.app"),
      settings=Settings(platform=platform, network=mock_network),
    )
    browser.manual = True
    mock_wda = mock.MagicMock()
    platform._wda = mock_wda

    session = mock.create_autospec(
      BrowserSessionRunGroup,
      instance=True,
      extra_flags=(),
    )
    session.network = mock.MagicMock()
    session.network.extra_flags.return_value = ()

    browser.start(session)
    mock_wda.stop_device_runner.assert_called_once_with()
    self.assertFalse(mock_wda.enabled)
    mock_wda.launch_app.assert_not_called()
    self.assertTrue(browser.is_running)

    self.host_platform.expect_sh(
      "xcrun",
      "devicectl",
      "device",
      "process",
      "launch",
      "--device",
      "00001111-11AA22BB33DD",
      "--terminate-existing",
      "--payload-url",
      "https://example.com",
      "com.apple.mobilesafari",
      result="",
    )
    browser.show_url("https://example.com", WindowTarget.SELF)
    mock_wda.open_url.assert_not_called()

    browser.force_quit()
    mock_wda.terminate_app.assert_not_called()
    # WDA stays disabled: nothing may reattach it after a manual run either.
    self.assertFalse(mock_wda.enabled)
    self.assertFalse(browser.is_running)

  def test_wda_start_with_env_vars(self) -> None:
    platform = self.setup_platform()
    mock_network = mock.MagicMock()
    mock_network.is_running = True
    mock_network.extra_flags.return_value = ()
    env_config = EnvConfig.parse({"env_vars": {"JSC_useBaselineJIT": "false"}})
    browser = SafariWdaIOS(
      "test-safari",
      platform.path("/Applications/Safari.app"),
      settings=Settings(
        platform=platform, network=mock_network, env_config=env_config
      ),
    )
    mock_wda = mock.MagicMock()
    platform._wda = mock_wda

    session = mock.create_autospec(
      BrowserSessionRunGroup,
      instance=True,
      extra_flags=(),
    )
    session.network = mock.MagicMock()
    session.network.extra_flags.return_value = ()

    browser.start(session)
    mock_wda.terminate_app.assert_called_once_with("com.apple.mobilesafari")
    mock_wda.launch_app.assert_called_once_with(
      "com.apple.mobilesafari",
      env_vars={
        "JSC_useBaselineJIT": "false",
        "__XPC_JSC_useBaselineJIT": "false",
      },
    )

  def test_wda_manual_mode_with_env_vars(self) -> None:
    platform = self.setup_platform()
    mock_network = mock.MagicMock()
    mock_network.is_running = True
    mock_network.extra_flags.return_value = ()
    env_config = EnvConfig.parse({"env_vars": {"JSC_useDFGJIT": "false"}})
    browser = SafariWdaIOS(
      "test-safari",
      platform.path("/Applications/Safari.app"),
      settings=Settings(
        platform=platform, network=mock_network, env_config=env_config
      ),
    )
    browser.manual = True
    mock_wda = mock.MagicMock()
    platform._wda = mock_wda

    session = mock.create_autospec(
      BrowserSessionRunGroup,
      instance=True,
      extra_flags=(),
    )
    session.network = mock.MagicMock()
    session.network.extra_flags.return_value = ()

    browser.start(session)
    with mock.patch.object(platform, "launch_app") as mock_launch_app:
      browser.show_url("https://example.com", WindowTarget.SELF)
      mock_launch_app.assert_called_once_with(
        "com.apple.mobilesafari",
        env_vars={
          "JSC_useDFGJIT": "false",
          "__XPC_JSC_useDFGJIT": "false",
        },
        payload_url="https://example.com",
      )

  def test_webdriver_ios_env_vars(self) -> None:
    platform = self.setup_platform()
    self.fs.create_file("/usr/bin/safaridriver", st_mode=0o755)
    self.host_platform.expect_sh(
      "/usr/bin/safaridriver",
      "--version",
      result="Included with Safari 17.1 (19616.2.9.11.7)",
    )
    env_config = EnvConfig.parse({"env_vars": {"JSC_useFTLJIT": "false"}})
    browser = SafariWebdriverIOS(
      "test-safari",
      platform.path("/Applications/Safari.app"),
      settings=Settings(platform=platform, env_config=env_config),
    )
    self.assertIsNone(browser._get_service_env())
    with (
      mock.patch.object(platform, "launch_app") as mock_launch_app,
      mock.patch.object(self.host_platform, "sleep") as mock_sleep,
    ):
      browser._launch_with_env_vars()
      mock_launch_app.assert_called_once_with(
        "com.apple.mobilesafari",
        env_vars={
          "JSC_useFTLJIT": "false",
          "__XPC_JSC_useFTLJIT": "false",
        },
      )
      mock_sleep.assert_called_once_with(SafariWebdriverIOS.ENV_LAUNCH_SETTLE)

      mock_launch_app.reset_mock()
      with (
        mock.patch(
          "crossbench.browsers.safari.webdriver.SafariWebDriver.quit",
          side_effect=RuntimeError("quit failed"),
        ),
        self.assertRaisesRegex(RuntimeError, "quit failed"),
      ):
        browser.quit()
      mock_launch_app.assert_called_once_with("com.apple.mobilesafari")

  def test_webdriver_ios_close_all_tabs_preserves_window_for_js(self) -> None:
    platform = self.setup_platform()
    self.fs.create_file("/usr/bin/safaridriver", st_mode=0o755)
    self.host_platform.expect_sh(
      "/usr/bin/safaridriver",
      "--version",
      result="Included with Safari 17.1 (19616.2.9.11.7)",
    )
    browser = SafariWebdriverIOS(
      "test-safari",
      platform.path("/Applications/Safari.app"),
      settings=Settings(platform=platform),
    )
    driver = FakeWebDriver(
      handles=["tab-1", "tab-2"],
      current_handle="tab-1",
      invalidate_session_on_last_close=False,
    )
    browser._private_driver = driver
    browser._is_running = True

    browser.close_all_tabs()

    self.assertEqual(driver.closed_handles, ["tab-2"])
    self.assertEqual(driver.window_handles, ["tab-1"])
    self.assertEqual(driver.urls_by_handle["tab-1"], "about:blank")
    self.assertEqual(browser.user_agent(), "FakeBrowser/123.0")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
