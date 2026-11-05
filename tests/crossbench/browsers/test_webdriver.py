# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence
from unittest import mock

import selenium.common.exceptions
import urllib3
from selenium import webdriver
from selenium.webdriver.remote.client_config import ClientConfig
from selenium.webdriver.remote.remote_connection import RemoteConnection
from typing_extensions import override

from crossbench import path as pth
from crossbench.browsers.safari.webdriver import SafariWebDriver
from crossbench.browsers.settings import Settings
from crossbench.browsers.version import UnknownBrowserVersion
from crossbench.browsers.webdriver import RemoteWebDriver, WebDriverBrowser
from crossbench.browsers.webview.webview import Webview
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.mock_helper import MacOsMockPlatform

if TYPE_CHECKING:
  from crossbench.browsers.version import BrowserVersion
  from crossbench.runner.groups.session import BrowserSessionRunGroup


class FakeSwitchTo:

  def __init__(self, driver: FakeWebDriver) -> None:
    self._driver: FakeWebDriver = driver

  def window(self, window_name: str) -> None:
    self._driver.switch_window(window_name)

  def new_window(self, type_hint: str = "tab") -> None:
    self._driver.open_new_window(type_hint)


class FakeTimeouts:

  def __init__(self) -> None:
    self.script: float = 30.0
    self.implicit_wait: float = 0.0
    self.page_load: float = 300.0


class FakeWebDriver(webdriver.Remote):
  """Stateful W3C-like WebDriver stub for window/session lifecycle tests."""

  def __init__(
      self,
      handles: Sequence[str] = ("tab-1",),
      current_handle: str | None = "tab-1",
      invalidate_session_on_last_close: bool = True,
  ) -> None:
    # Intentionally skip super().__init__() to avoid network connections.
    self.session_id: str | None = "fake-session-id"
    self.command_executor: RemoteConnection = RemoteConnection(
        client_config=ClientConfig(remote_server_addr="http://127.0.0.1:9999"))
    self._handles: list[str] = list(handles)
    self._current_handle: str | None = current_handle
    self._invalidate_on_last_close: bool = invalidate_session_on_last_close
    self._session_valid: bool = True
    self._switch_to: FakeSwitchTo = FakeSwitchTo(self)
    self._timeouts: FakeTimeouts = FakeTimeouts()
    self.closed_handles: list[str] = []
    self.urls_by_handle: dict[str, str] = {
        handle: f"https://example.com/{handle}" for handle in handles
    }
    self._capabilities: dict[str, object] = {
        "browserVersion": "123.0.4567.89",
        "setWindowRect": False,
    }
    self.quit_called: bool = False

  @property
  @override
  def capabilities(self) -> dict[str, object]:
    return self._capabilities

  @property
  @override
  def current_url(self) -> str:
    handle = self._require_current_window()
    return self.urls_by_handle[handle]

  @property
  @override
  def timeouts(self) -> FakeTimeouts:  # type: ignore[override]
    return self._timeouts

  @timeouts.setter
  def timeouts(self, value: FakeTimeouts) -> None:
    self._timeouts = value

  @override
  def set_script_timeout(self, time_to_wait: float) -> None:
    self._timeouts.script = time_to_wait

  def _check_session(self) -> None:
    if not self._session_valid:
      raise selenium.common.exceptions.InvalidSessionIdException(
          "WebDriver session was invalidated after closing the last window")

  def _require_current_window(self) -> str:
    self._check_session()
    if (self._current_handle is None or
        self._current_handle not in self._handles):
      raise selenium.common.exceptions.NoSuchWindowException(
          "Browsing context has been discarded")
    return self._current_handle

  @property
  @override
  def window_handles(self) -> list[str]:
    self._check_session()
    return list(self._handles)

  @property
  @override
  def current_window_handle(self) -> str:
    return self._require_current_window()

  @property
  @override
  def switch_to(self) -> FakeSwitchTo:  # type: ignore[override]
    self._check_session()
    return self._switch_to

  def switch_window(self, handle: str) -> None:
    self._check_session()
    if handle not in self._handles:
      raise selenium.common.exceptions.NoSuchWindowException(
          f"No such window: {handle}")
    self._current_handle = handle

  def open_new_window(self, type_hint: str = "tab") -> None:
    del type_hint
    self._check_session()
    new_handle = f"tab-{len(self._handles) + len(self.closed_handles) + 1}"
    self._handles.append(new_handle)
    self._current_handle = new_handle
    self.urls_by_handle[new_handle] = "about:blank"

  @override
  def close(self) -> None:
    handle = self._require_current_window()
    self._handles.remove(handle)
    self.closed_handles.append(handle)
    self.urls_by_handle.pop(handle, None)
    self._current_handle = None
    if not self._handles and self._invalidate_on_last_close:
      self._session_valid = False

  @override
  def get(self, url: str) -> None:
    handle = self._require_current_window()
    self.urls_by_handle[handle] = url

  @override
  def execute_script(self, script: str, *args: object) -> object:
    del args
    handle = self._require_current_window()
    if "userAgent" in script:
      return "FakeBrowser/123.0"
    return self.urls_by_handle[handle]

  @override
  def quit(self) -> None:
    self.quit_called = True
    self._handles.clear()
    self._current_handle = None
    self._session_valid = False


class StubWebDriverBrowser(WebDriverBrowser):
  """Minimal concrete WebDriverBrowser exercising base close_all_tabs/quit."""

  @classmethod
  @override
  def type_name(cls) -> str:
    return "stub"

  def __init__(self,
               label: str,
               driver: webdriver.Remote,
               settings: Settings | None = None) -> None:
    self._private_driver: webdriver.Remote = driver
    super().__init__(label=label, path=None, settings=settings)

  @override
  def _extract_version(self) -> BrowserVersion:
    return UnknownBrowserVersion((123, 0, 0, 0), version_str="123.0.0.0")

  @override
  def _find_driver(self) -> pth.AnyPath:
    return pth.AnyPath("/usr/bin/fakedriver")

  @override
  def _start_driver(self, session: BrowserSessionRunGroup,
                    driver_path: pth.AnyPath) -> webdriver.Remote:
    del session, driver_path
    return self._private_driver

  @override
  def _setup_cache_dir(self) -> pth.AnyPath | None:
    return None

  @override
  def _validate_driver_version(self) -> None:
    pass

  @override
  def validate_binary(self) -> None:
    pass


class WebDriverBrowserTestCase(BaseCrossbenchTestCase):

  def _create_remote_browser(self, driver: webdriver.Remote) -> RemoteWebDriver:
    browser = RemoteWebDriver("test-driver", driver)
    browser._is_running = True
    return browser

  def test_close_all_tabs_keeps_current_tab_and_navigates_to_blank(
      self) -> None:
    driver = FakeWebDriver(
        handles=["tab-1", "tab-2", "tab-3"], current_handle="tab-2")
    browser = self._create_remote_browser(driver)

    browser.close_all_tabs()

    self.assertEqual(driver.closed_handles, ["tab-1", "tab-3"])
    self.assertEqual(driver.window_handles, ["tab-2"])
    self.assertEqual(driver.current_window_handle, "tab-2")
    self.assertEqual(driver.urls_by_handle["tab-2"], "about:blank")
    self.assertEqual(browser.user_agent(), "FakeBrowser/123.0")

  def test_close_all_tabs_single_tab_preserves_session(self) -> None:
    driver = FakeWebDriver(
        handles=["tab-1"],
        current_handle="tab-1",
        invalidate_session_on_last_close=True)
    browser = self._create_remote_browser(driver)

    browser.close_all_tabs()

    self.assertEqual(driver.closed_handles, [])
    self.assertEqual(driver.window_handles, ["tab-1"])
    self.assertEqual(driver.current_window_handle, "tab-1")
    self.assertEqual(driver.urls_by_handle["tab-1"], "about:blank")
    self.assertEqual(browser.user_agent(), "FakeBrowser/123.0")

  def test_close_all_tabs_falls_back_when_current_handle_missing(self) -> None:
    driver = FakeWebDriver(handles=["tab-1", "tab-2"], current_handle=None)
    browser = self._create_remote_browser(driver)

    browser.close_all_tabs()

    self.assertEqual(driver.closed_handles, ["tab-1"])
    self.assertEqual(driver.window_handles, ["tab-2"])
    self.assertEqual(driver.current_window_handle, "tab-2")
    self.assertEqual(driver.urls_by_handle["tab-2"], "about:blank")

  def test_close_all_tabs_stale_current_handle_keeps_last_tab(self) -> None:
    driver = FakeWebDriver(
        handles=["tab-1", "tab-2"], current_handle="stale-tab")
    browser = self._create_remote_browser(driver)

    browser.close_all_tabs()

    self.assertEqual(driver.closed_handles, ["tab-1"])
    self.assertEqual(driver.window_handles, ["tab-2"])
    self.assertEqual(driver.current_window_handle, "tab-2")
    self.assertEqual(driver.urls_by_handle["tab-2"], "about:blank")

  def test_close_all_tabs_empty_handles_is_noop(self) -> None:
    driver = FakeWebDriver(handles=[], current_handle=None)
    browser = self._create_remote_browser(driver)

    with mock.patch.object(browser, "show_url") as mock_show_url:
      browser.close_all_tabs()
      mock_show_url.assert_not_called()

  def test_close_all_tabs_handles_http_errors(self) -> None:
    mock_driver = mock.MagicMock(spec=webdriver.Remote)
    mock_driver.capabilities = {
        "browserVersion": "123.0.4567.89",
        "setWindowRect": False,
    }
    type(mock_driver).window_handles = mock.PropertyMock(
        side_effect=urllib3.exceptions.MaxRetryError(mock.Mock(), "/windows"))
    browser = self._create_remote_browser(mock_driver)

    browser.close_all_tabs()
    mock_driver.close.assert_not_called()

  def test_quit_closes_extra_tabs_and_final_window(self) -> None:
    driver = FakeWebDriver(
        handles=["tab-1", "tab-2"],
        current_handle="tab-1",
        invalidate_session_on_last_close=False)
    browser = StubWebDriverBrowser(
        "stub", driver, settings=Settings(platform=self.platform))
    browser._is_running = True
    if self.platform.is_macos:
      self.platform.expect_sh(
          "/usr/bin/osascript",
          "-e",
          f'\n  tell application "{browser.app_path}"\n'
          "    quit\n  end tell\n      ",
      )

    browser.quit()

    self.assertEqual(driver.closed_handles, ["tab-2", "tab-1"])
    self.assertTrue(driver.quit_called)
    self.assertFalse(browser.is_running)

  def test_macos_quit_closes_extra_tabs_and_final_window(self) -> None:
    macos_platform = MacOsMockPlatform()
    driver = FakeWebDriver(
        handles=["tab-1", "tab-2"],
        current_handle="tab-1",
        invalidate_session_on_last_close=False)
    browser = StubWebDriverBrowser(
        "stub", driver, settings=Settings(platform=macos_platform))
    browser._is_running = True
    macos_platform.expect_sh(
        "/usr/bin/osascript",
        "-e",
        f'\n  tell application "{browser.app_path}"\n'
        "    quit\n  end tell\n      ",
    )

    browser.quit()

    self.assertEqual(driver.closed_handles, ["tab-2", "tab-1"])
    self.assertTrue(driver.quit_called)
    self.assertFalse(browser.is_running)
    self.assertSequenceEqual(macos_platform.sh_results, [])

  def test_macos_safari_close_all_tabs_preserves_session(self) -> None:
    macos_platform = MacOsMockPlatform()
    safari_bin = macos_platform.path(
        "/Applications/Safari.app/Contents/MacOS/Safari")
    safaridriver_bin = macos_platform.path("/usr/bin/safaridriver")
    if not self.fs.exists(safari_bin):
      self.fs.create_file(safari_bin, st_mode=0o755)
    if not self.fs.exists(safaridriver_bin):
      self.fs.create_file(safaridriver_bin, st_mode=0o755)
    macos_platform.expect_sh(safari_bin, "--version", result="Safari 17.4")
    macos_platform.expect_sh(
        safaridriver_bin,
        "--version",
        result="Included with Safari 17.4 (19618.1.15.11.14)")
    browser = SafariWebDriver(
        "safari",
        macos_platform.path("/Applications/Safari.app"),
        settings=Settings(platform=macos_platform))
    driver = FakeWebDriver(
        handles=["tab-1", "tab-2"],
        current_handle="tab-1",
        invalidate_session_on_last_close=True)
    browser._private_driver = driver
    browser._is_running = True

    browser.close_all_tabs()

    self.assertEqual(driver.closed_handles, ["tab-2"])
    self.assertEqual(driver.window_handles, ["tab-1"])
    self.assertEqual(driver.urls_by_handle["tab-1"], "about:blank")
    self.assertEqual(browser.user_agent(), "FakeBrowser/123.0")
    self.assertSequenceEqual(macos_platform.sh_results, [])

  def test_webview_close_all_tabs_raises_not_implemented(self) -> None:
    mock_webview = mock.MagicMock(spec=Webview)
    with self.assertRaises(NotImplementedError):
      Webview.close_all_tabs(mock_webview)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
