# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import pathlib
from unittest import mock

from crossbench.benchmarks.loading.config.pages import PagesConfig
from crossbench.benchmarks.loading.loading_benchmark import LoadingPageFilter
from crossbench.benchmarks.loading.page.base import Page
from crossbench.browsers.settings import Settings
from crossbench.cli.config.secrets import (
  GoogleUsernamePassword,
  Secrets,
  UsernamePassword,
)
from crossbench.exception import MultiException
from crossbench.flags.base import Flags
from crossbench.plt.android_adb import Adb, AndroidAdbPlatform
from crossbench.runner.groups.session import BrowserSessionRunGroup
from crossbench.runner.run import Run
from tests import test_helper
from tests.crossbench.action_runner.action_runner_test_case import (
  ActionRunnerTestCase,
)
from tests.crossbench.mock_browser import (
  MockChromeAndroidStable,
  MockChromeStable,
)
from tests.crossbench.mock_helper import (
  ChromeOsSshMockPlatform,
  LinuxMockPlatform,
)
from tests.crossbench.runner.helper import MockRun, MockRunner


class ChromeOSLoginTestCase(ActionRunnerTestCase):
  _CONFIG_DATA = {
    "secrets": {
      "google": {
        "username": "test",
        "password": "s3cr3t",
      },
    },
    "pages": {
      "Google Story": {
        "login": "google",
        "actions": [
          {
            "action": "get",
            "url": "https://www.google.com",
          }
        ],
      },
    },
  }

  def setUp(self) -> None:
    super().setUp()
    self.host_platform = LinuxMockPlatform()
    self.platform = ChromeOsSshMockPlatform(
      host_platform=self.host_platform,
      host="1.1.1.1",
      port="1234",
      ssh_port="22",
      ssh_user="root",
    )

    self.platform.expect_sh("[", "-e", "/usr/bin/google-chrome", "]", result="")
    self.platform.expect_sh("[", "-f", "/usr/bin/google-chrome", "]", result="")

    self.browser = MockChromeStable(
      "mock browser", settings=Settings(platform=self.platform)
    )
    self.runner = MockRunner()
    self.root_dir = pathlib.Path()
    self.session = BrowserSessionRunGroup(
      self.runner.env,
      self.runner.probes,
      self.browser,
      Flags(),
      1,
      self.root_dir,
      True,
      True,
    )
    self.mock_run = MockRun(self.runner, self.session, "run 1")
    self.action_runner = self.mock_run.action_runner

  def expect_successful_google_login(self):
    # Wait for readystate interactive
    self.browser.expect_js(result=True)

    # Wait for email field
    self.browser.expect_js(result=True)
    # Click submit email
    self.browser.expect_js(result=None)

    # Wait for password field
    self.browser.expect_js(result=True)
    # Click submit password
    self.browser.expect_js(result=None)

    # Wait for redirect after password
    self.browser.expect_js(result=True)
    # Wait for readystate complete
    self.browser.expect_js(result=True)
    # Return successful login URL
    self.browser.expect_js(result="https://myaccount.google.com")
    # Check for suspicious activity
    self.browser.expect_js(result=False)

  def test_google_account(self):
    config = PagesConfig.parse(self._CONFIG_DATA)
    page = LoadingPageFilter.from_config(Page, self.mock_args(), config).stories

    self.expect_successful_google_login()

    self.mock_run.story_secrets = page[0].secrets
    self.assertIsNotNone(config.pages[0].login)
    config.pages[0].login.run_with(self.action_runner)

  def test_logged_in_google_account(self):
    config = PagesConfig.parse(self._CONFIG_DATA)
    page = LoadingPageFilter.from_config(Page, self.mock_args(), config).stories

    self.browser.expect_is_logged_in(GoogleUsernamePassword("test", "s3cr3t"))

    self.mock_run.story_secrets = page[0].secrets
    self.assertIsNotNone(config.pages[0].login)
    config.pages[0].login.run_with(self.action_runner)

  def test_logged_in_non_google_account(self):
    config = PagesConfig.parse(self._CONFIG_DATA)
    page = LoadingPageFilter.from_config(Page, self.mock_args(), config).stories

    self.browser.expect_is_logged_in(UsernamePassword("test", "s3cr3t"))

    self.expect_successful_google_login()

    self.mock_run.story_secrets = page[0].secrets
    self.assertIsNotNone(config.pages[0].login)
    config.pages[0].login.run_with(self.action_runner)

  def test_full_account_maintenance_flow(self):
    config = PagesConfig.parse(self._CONFIG_DATA)
    page = LoadingPageFilter.from_config(Page, self.mock_args(), config).stories

    # Wait for readystate interactive
    self.browser.expect_js(result=True)

    # Wait for email field
    self.browser.expect_js(result=True)
    # Click submit email
    self.browser.expect_js(result=None)

    # Wait for password field
    self.browser.expect_js(result=True)
    # Click submit password
    self.browser.expect_js(result=None)

    # Wait for redirect after password
    self.browser.expect_js(result=True)
    # Wait for readystate complete
    self.browser.expect_js(result=True)

    # Return passkey URL
    passkey_url = (
      "https://accounts.google.com/v3/signin/speedbump/passkeyenrollment"
    )
    self.browser.expect_js(result=passkey_url)
    # Wait for skip element
    self.browser.expect_js(result={"count": 1})
    # Click skip element
    self.browser.expect_js(result={"count": 1})
    # Wait for URL change
    self.browser.expect_js(result=True)
    # Wait for ready state complete
    self.browser.expect_js(result=True)

    # Return passkey URL
    self.browser.expect_js(result="https://gds.google.com/web/recoveryoptions")
    # Wait for skip element
    self.browser.expect_js(result={"count": 1})
    # Click skip element
    self.browser.expect_js(result={"count": 1})
    # Wait for URL change
    self.browser.expect_js(result=True)
    # Wait for ready state complete
    self.browser.expect_js(result=True)

    # Return passkey URL
    self.browser.expect_js(result="https://gds.google.com/web/homeaddress")
    # Wait for skip element
    self.browser.expect_js(result={"count": 1})
    # Click skip element
    self.browser.expect_js(result={"count": 1})
    # Wait for URL change
    self.browser.expect_js(result=True)
    # Wait for ready state complete
    self.browser.expect_js(result=True)

    # Return successful login URL
    self.browser.expect_js(result="https://myaccount.google.com")

    # Return suspicious activity is present
    self.browser.expect_js(result=True)
    # Click suspicious activity button
    self.browser.expect_js(result={"count": 1})
    # Wait for 'yes' button
    self.browser.expect_js(result={"count": 1})
    # Click 'yes' button
    self.browser.expect_js(result={"count": 1})
    # Wait 'yes' button not present.
    self.browser.expect_js(result={"count": 1})

    self.mock_run.story_secrets = page[0].secrets
    self.assertIsNotNone(config.pages[0].login)
    config.pages[0].login.run_with(self.action_runner)


class AndroidOsLoginTestCase(ActionRunnerTestCase):
  def setUp(self) -> None:
    super().setUp()
    self.host_platform = LinuxMockPlatform()
    self.platform = self.host_platform
    adb_bin = pathlib.Path("/usr/bin/adb")
    self.fs.create_file(adb_bin, st_size=100)
    adb_devices_out = (
      "List of devices attached\n"
      "emulator-5554 device product:sdk model:Phone device:emu\n"
    )
    self.host_platform.expect_sh(adb_bin, "start-server")
    self.host_platform.expect_sh(
      adb_bin, "devices", "-l", result=adb_devices_out
    )
    adb = Adb(self.host_platform, "emulator-5554", adb_bin)
    self.adb_platform = AndroidAdbPlatform(
      self.host_platform, "emulator-5554", adb=adb
    )
    self.secret = GoogleUsernamePassword(
      "ota@gmail.com",
      "secret_pw",
      account_util_apk="gs://bucket/GoogleAccountUtil.apk",
    )
    self.browser = MockChromeAndroidStable(
      "mock android browser",
      settings=Settings(
        platform=self.adb_platform, secrets=Secrets(google=self.secret)
      ),
    )
    self.runner = MockRunner()
    self.session = BrowserSessionRunGroup(
      self.runner.env,
      self.runner.probes,
      self.browser,
      Flags(),
      1,
      pathlib.Path(),
      True,
      True,
    )
    self.mock_run = MockRun(self.runner, self.session, "run 1")
    self.action_runner = self.mock_run.action_runner

  def test_google_os_login_provisions_and_links_chrome(self) -> None:
    config = PagesConfig.parse(
      {
        "pages": {
          "OS Login Story": {
            "login": "google-os",
            "actions": [{"action": "get", "url": "https://www.google.com"}],
          }
        }
      }
    )
    mock_ui = mock.MagicMock()
    avatar_obj = mock.MagicMock(description="Signed out. Sign in.")
    avatar_obj.click.return_value = True
    continue_obj = mock.MagicMock()
    continue_obj.wait.click.return_value = True
    history_sync_obj = mock.MagicMock()
    history_sync_obj.wait.exists.return_value = True
    decline_obj = mock.MagicMock()
    decline_obj.wait.click.return_value = True

    def fake_ui(**kwargs: object) -> mock.MagicMock:
      pattern = str(kwargs.get("resourceIdMatches", ""))
      if "optional_toolbar_button" in pattern:
        return avatar_obj
      if "account_picker_continue_as_button" in pattern:
        return continue_obj
      if "history_sync" in pattern:
        return history_sync_obj
      if "button_secondary" in pattern:
        return decline_obj
      return mock.MagicMock()

    mock_ui.side_effect = fake_ui
    mock_ui.find.return_value = []
    mock_ad = mock.MagicMock(ui=mock_ui)
    mock_ctx = mock.MagicMock()
    mock_ctx.__enter__.return_value = mock_ad

    with (
      mock.patch.object(
        self.adb_platform, "provision_google_account"
      ) as mock_provision,
      mock.patch.object(
        self.adb_platform, "uiautomator_device", return_value=mock_ctx
      ),
      mock.patch.object(self.adb_platform, "sleep"),
    ):
      assert config.pages[0].login is not None
      config.pages[0].login.run_with(self.action_runner)

    mock_provision.assert_called_once_with(self.secret)
    self.assertEqual(self.browser.url_list, ["chrome://newtab/"])
    avatar_obj.click.assert_called_once_with()
    continue_obj.wait.click.assert_called_once()
    decline_obj.wait.click.assert_called_once()

  def test_web_google_login_ignores_account_util_apk_in_shared_secrets(
    self,
  ) -> None:
    config = PagesConfig.parse(
      {
        "pages": {
          "Web Login Story": {
            "login": "google",
            "actions": [{"action": "get", "url": "https://www.google.com"}],
          }
        }
      }
    )
    self.browser.expect_js(result=True)
    self.browser.expect_js(result=True)
    self.browser.expect_js(result=None)
    self.browser.expect_js(result=True)
    self.browser.expect_js(result=None)
    self.browser.expect_js(result=True)
    self.browser.expect_js(result=True)
    self.browser.expect_js(result="https://myaccount.google.com")
    self.browser.expect_js(result=False)

    with (
      mock.patch.object(
        self.adb_platform, "provision_google_account"
      ) as mock_provision,
      mock.patch.object(self.adb_platform, "inject_input_events"),
    ):
      assert config.pages[0].login is not None
      config.pages[0].login.run_with(self.action_runner)
    mock_provision.assert_not_called()

  def test_google_os_login_raises_on_persistent_identity_error(self) -> None:
    config = PagesConfig.parse(
      {
        "pages": {
          "OS Login Story": {
            "login": "google-os",
            "actions": [{"action": "get", "url": "https://www.google.com"}],
          }
        }
      }
    )
    mock_ui = mock.MagicMock()
    mock_ui.return_value = mock.MagicMock(
      description="Signed in as ota@gmail.com"
    )
    mock_ui.find.return_value = [{"text": "Verify it's you"}]
    mock_ad = mock.MagicMock(ui=mock_ui)
    mock_ctx = mock.MagicMock()
    mock_ctx.__enter__.return_value = mock_ad

    with (
      mock.patch.object(
        self.adb_platform, "provision_google_account"
      ) as mock_provision,
      mock.patch.object(
        self.adb_platform, "uiautomator_device", return_value=mock_ctx
      ),
      self.assertRaisesRegex(RuntimeError, "identity error persisted"),
    ):
      assert config.pages[0].login is not None
      config.pages[0].login.run_with(self.action_runner)
    self.assertEqual(
      mock_provision.call_args_list,
      [mock.call(self.secret), mock.call(self.secret, force=True)],
    )

  def test_google_os_login_requires_account_util_apk(self) -> None:
    self.browser = MockChromeAndroidStable(
      "mock android browser",
      settings=Settings(
        platform=self.adb_platform,
        secrets=Secrets(google=GoogleUsernamePassword("ota@gmail.com", "pw")),
      ),
    )
    self.session = BrowserSessionRunGroup(
      self.runner.env,
      self.runner.probes,
      self.browser,
      Flags(),
      1,
      pathlib.Path(),
      True,
      True,
    )
    self.mock_run = MockRun(self.runner, self.session, "run 1")
    config = PagesConfig.parse(
      {
        "pages": {
          "OS Login Story": {
            "login": "google-os",
            "actions": [{"action": "get", "url": "https://www.google.com"}],
          }
        }
      }
    )
    with self.assertRaisesRegex(ValueError, "account_util_apk"):
      assert config.pages[0].login is not None
      config.pages[0].login.run_with(self.mock_run.action_runner)

  def _make_run_for_browser(self, browser: MockChromeStable) -> MockRun:
    session = BrowserSessionRunGroup(
      self.runner.env,
      self.runner.probes,
      browser,
      Flags(),
      1,
      pathlib.Path(),
      True,
      True,
    )
    return MockRun(self.runner, session, "run 1")

  def _story_from_config(self, config: PagesConfig) -> Page:
    args = self.mock_args()
    args.run_login = True
    args.run_setup = True
    args.about_blank_duration = 0
    (story,) = LoadingPageFilter.from_config(Page, args, config).stories
    return story

  def test_google_os_login_with_no_start_browser_defers_browser_login(
    self,
  ) -> None:
    browser = MockChromeAndroidStable(
      "mock android browser",
      settings=Settings(
        platform=self.adb_platform,
        secrets=Secrets(google=self.secret),
        start_browser=False,
      ),
    )
    run = self._make_run_for_browser(browser)
    config = PagesConfig.parse(
      {
        "pages": {
          "OS Login Story": {
            "login": "google-os",
            "actions": [
              {
                "action": "start_browser",
                "startup_urls": ["https://mail.google.com/"],
              },
              {"action": "stop_browser"},
              {"action": "start_browser"},
            ],
          }
        }
      }
    )
    story = self._story_from_config(config)
    run._story = story
    avatar_obj = mock.MagicMock(description="Signed in as ota@gmail.com")
    mock_ui = mock.MagicMock(return_value=avatar_obj)
    mock_ui.find.return_value = []
    mock_ctx = mock.MagicMock()
    mock_ctx.__enter__.return_value = mock.MagicMock(ui=mock_ui)

    def fake_start_browser(startup_urls: tuple[str, ...] = ()) -> None:
      browser._is_running = True
      browser.url_list.extend(startup_urls)

    def fake_stop_browser() -> None:
      browser._is_running = False

    with (
      mock.patch.object(
        self.adb_platform, "provision_google_account"
      ) as mock_provision,
      mock.patch.object(
        self.adb_platform, "uiautomator_device", return_value=mock_ctx
      ) as mock_uiautomator,
      mock.patch.object(self.adb_platform, "trace_mark"),
      mock.patch.object(
        run.browser_session, "start_browser", side_effect=fake_start_browser
      ) as mock_start,
      mock.patch.object(
        run.browser_session, "stop_browser", side_effect=fake_stop_browser
      ) as mock_stop,
    ):
      story.setup(run)
      mock_provision.assert_called_once_with(self.secret)
      mock_start.assert_not_called()
      mock_uiautomator.assert_not_called()
      self.assertFalse(browser.is_running)

      story.run(run)
      story.teardown(run)

    mock_provision.assert_called_once_with(self.secret)
    mock_uiautomator.assert_called_once_with(root_device=False)
    self.assertEqual(mock_start.call_args_list, [mock.call(), mock.call(())])
    mock_stop.assert_called_once_with()
    self.assertEqual(
      browser.url_list, ["chrome://newtab/", "https://mail.google.com/"]
    )
    self.assertIn("crossbench-login-start", browser.performance_marks)
    self.assertIn("crossbench-login-end", browser.performance_marks)

  def test_google_os_login_with_no_start_browser_never_starts_browser(
    self,
  ) -> None:
    browser = MockChromeAndroidStable(
      "mock android browser",
      settings=Settings(
        platform=self.adb_platform,
        secrets=Secrets(google=self.secret),
        start_browser=False,
      ),
    )
    run = self._make_run_for_browser(browser)
    config = PagesConfig.parse(
      {
        "pages": {
          "OS Native App Story": {
            "login": "google-os",
            "actions": [{"action": "wait", "duration": "0.1s"}],
          }
        }
      }
    )
    story = self._story_from_config(config)
    run._story = story
    with (
      mock.patch.object(
        self.adb_platform, "provision_google_account"
      ) as mock_provision,
      mock.patch.object(
        self.adb_platform, "uiautomator_device"
      ) as mock_uiautomator,
      mock.patch.object(self.adb_platform, "trace_mark"),
      mock.patch.object(run.browser_session, "start_browser") as mock_start,
    ):
      story.setup(run)
      story.run(run)
      story.teardown(run)

    mock_provision.assert_called_once_with(self.secret)
    mock_start.assert_not_called()
    mock_uiautomator.assert_not_called()
    self.assertFalse(browser.is_running)

  def test_web_google_login_with_no_start_browser_defers_to_start_browser(
    self,
  ) -> None:
    browser = MockChromeAndroidStable(
      "mock android browser",
      settings=Settings(
        platform=self.adb_platform,
        secrets=Secrets(google=self.secret),
        start_browser=False,
      ),
    )
    run = self._make_run_for_browser(browser)
    config = PagesConfig.parse(
      {
        "pages": {
          "Web Login Story": {
            "login": "google",
            "actions": [
              {
                "action": "start_browser",
                "startup_urls": ["https://docs.google.com/"],
              }
            ],
          }
        }
      }
    )
    story = self._story_from_config(config)
    run._story = story
    browser.expect_js(result=True)
    browser.expect_js(result=True)
    browser.expect_js(result=None)
    browser.expect_js(result=True)
    browser.expect_js(result=None)
    browser.expect_js(result=True)
    browser.expect_js(result=True)
    browser.expect_js(result="https://myaccount.google.com")
    browser.expect_js(result=False)

    def fake_start_browser(startup_urls: tuple[str, ...] = ()) -> None:
      browser._is_running = True
      browser.url_list.extend(startup_urls)

    with (
      mock.patch.object(self.adb_platform, "inject_input_events"),
      mock.patch.object(self.adb_platform, "trace_mark"),
      mock.patch.object(
        run.browser_session, "start_browser", side_effect=fake_start_browser
      ) as mock_start,
    ):
      story.setup(run)
      mock_start.assert_not_called()
      self.assertFalse(browser.is_running)
      self.assertEqual(browser.url_list, [])

      story.run(run)
      story.teardown(run)

    mock_start.assert_called_once_with()
    self.assertTrue(browser.is_running)
    self.assertEqual(browser.url_list[-1], "https://docs.google.com/")

  def test_login_rejects_android_bypass_oobe_false(self) -> None:
    oobe_platform = AndroidAdbPlatform(
      self.host_platform,
      "emulator-5554",
      adb=self.adb_platform.adb,
      bypass_oobe=False,
    )
    browser = MockChromeAndroidStable(
      "mock android browser",
      settings=Settings(
        platform=oobe_platform,
        secrets=Secrets(google=self.secret),
        start_browser=False,
      ),
    )
    run = self._make_run_for_browser(browser)
    for login_type in ("google", "google-os"):
      config = PagesConfig.parse(
        {
          "pages": {
            "Story": {
              "login": login_type,
              "actions": [{"action": "start_browser"}],
            }
          }
        }
      )
      (story,) = LoadingPageFilter.from_config(
        Page, self.mock_args(), config
      ).stories
      run._story = story
      with self.assertRaisesRegex(ValueError, "bypass_oobe=False"):
        Run.validate_env(run, self.runner.env)

  def test_login_rejects_unsupported_platform_combinations(self) -> None:
    MockChromeStable.setup_fs(self.fs, self.host_platform)
    desktop_browser = MockChromeStable(
      "desktop chrome",
      settings=Settings(
        platform=self.host_platform, secrets=Secrets(google=self.secret)
      ),
    )
    desktop_run = self._make_run_for_browser(desktop_browser)
    config = PagesConfig.parse(
      {
        "pages": {
          "Story": {
            "login": "google-os",
            "actions": [{"action": "get", "url": "https://www.google.com"}],
          }
        }
      }
    )
    (story,) = LoadingPageFilter.from_config(
      Page, self.mock_args(), config
    ).stories
    desktop_run._story = story
    with self.assertRaisesRegex(
      NotImplementedError, "only supported on Android"
    ):
      Run.validate_env(desktop_run, self.runner.env)

    cros_platform = ChromeOsSshMockPlatform(
      host_platform=self.host_platform,
      host="1.1.1.1",
      port="1234",
      ssh_port="22",
      ssh_user="root",
    )
    cros_platform.expect_sh("[", "-e", "/usr/bin/google-chrome", "]")
    cros_platform.expect_sh("[", "-f", "/usr/bin/google-chrome", "]")
    cros_browser = MockChromeStable(
      "cros chrome",
      settings=Settings(
        platform=cros_platform,
        secrets=Secrets(google=self.secret),
        start_browser=False,
      ),
    )
    cros_run = self._make_run_for_browser(cros_browser)
    cros_run._story = story
    with self.assertRaisesRegex(NotImplementedError, "--no-start-browser"):
      Run.validate_env(cros_run, self.runner.env)

  def test_login_requires_google_secret(self) -> None:
    browser = MockChromeAndroidStable(
      "mock android browser",
      settings=Settings(platform=self.adb_platform, start_browser=False),
    )
    run = self._make_run_for_browser(browser)
    os_story = self._story_from_config(
      PagesConfig.parse(
        {
          "pages": {
            "Story": {
              "login": "google-os",
              "actions": [{"action": "start_browser"}],
            }
          }
        }
      )
    )
    run._story = os_story
    with self.assertRaisesRegex(RuntimeError, "No google login provided"):
      Run.validate_env(run, self.runner.env)

    web_story = self._story_from_config(
      PagesConfig.parse(
        {
          "pages": {
            "Story": {
              "login": "google",
              "actions": [{"action": "start_browser"}],
            }
          }
        }
      )
    )
    run._story = web_story

    def fake_start_browser(startup_urls: tuple[str, ...] = ()) -> None:
      del startup_urls
      browser._is_running = True

    with (
      mock.patch.object(self.adb_platform, "trace_mark"),
      mock.patch.object(
        run.browser_session, "start_browser", side_effect=fake_start_browser
      ),
      self.assertRaisesRegex(MultiException, "No google login provided"),
    ):
      web_story.setup(run)
      web_story.run(run)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
