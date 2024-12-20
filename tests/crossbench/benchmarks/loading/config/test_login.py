# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
from unittest import mock

from crossbench.action_runner.basic_action_runner import BasicActionRunner
from crossbench.benchmarks.loading.config.pages import PagesConfig
from crossbench.benchmarks.loading.loading_benchmark import LoadingPageFilter
from crossbench.browsers.settings import Settings
from crossbench.cli.config.secrets import Secret
from crossbench.cli.config.secret_type import SecretType
from crossbench.flags.base import Flags
from crossbench.runner.groups.session import BrowserSessionRunGroup
from tests import test_helper
from tests.crossbench.action_runner.action_runner_test_case import ActionRunnerTestCase
from tests.crossbench.mock_browser import MockChromeStable
from tests.crossbench.mock_helper import (ChromeOsSshMockPlatform,
                                          LinuxMockPlatform)
from tests.crossbench.runner.helper import MockRun, MockRunner


class ChromeOSLoginTestCase(ActionRunnerTestCase):
  _CONFIG_DATA = {
      "secrets": {
          "google": {
              "username": "test",
              "password": "s3cr3t"
          }
      },
      "pages": {
          "Google Story": {
              "login": "google",
              "actions": [{
                  "action": "get",
                  "url": "https://www.google.com"
              },]
          }
      }
  }

  def setUp(self) -> None:
    super().setUp()
    self.host_platform = LinuxMockPlatform()
    self.platform = ChromeOsSshMockPlatform(
        host_platform=self.host_platform,
        host="1.1.1.1",
        port="1234",
        ssh_port="22",
        ssh_user="root")

    self.platform.expect_sh("[", "-e", "/usr/bin/google-chrome", "]", result="")
    self.platform.expect_sh("[", "-f", "/usr/bin/google-chrome", "]", result="")

    self.browser = MockChromeStable(
        "mock browser", settings=Settings(platform=self.platform))
    self.runner = MockRunner()
    self.root_dir = pathlib.Path()
    self.session = BrowserSessionRunGroup(self.runner.env,
                                          self.runner.probes, self.browser,
                                          Flags(), 1, self.root_dir, True, True)
    self.run = MockRun(self.runner, self.session, "run 1")

    self.action_runner = BasicActionRunner()
    self.mock_args = mock.Mock()

  def expect_google_login(self):
    self.browser.expect_js(result=True)
    self.browser.expect_js(result=True)
    self.browser.expect_js(result=True)
    self.browser.expect_js(result=True)
    self.browser.expect_js(result=True)
    self.browser.expect_js(result=True)
    self.browser.expect_js(result=True)

  def test_google_account(self):
    config = PagesConfig.parse(self._CONFIG_DATA)
    page = LoadingPageFilter.stories_from_config(self.mock_args, config)

    self.expect_google_login()

    config.pages[0].login.run_with(self.action_runner, self.run, page[0])

  def test_logged_in_google_account(self):
    config = PagesConfig.parse(self._CONFIG_DATA)
    page = LoadingPageFilter.stories_from_config(self.mock_args, config)

    self.browser.expect_is_logged_in(
        Secret(SecretType.GOOGLE, "test", "s3cr3t"))

    config.pages[0].login.run_with(self.action_runner, self.run, page[0])

  def test_logged_in_non_google_account(self):
    config = PagesConfig.parse(self._CONFIG_DATA)
    page = LoadingPageFilter.stories_from_config(self.mock_args, config)

    self.browser.expect_is_logged_in(Secret(None, "test", "s3cr3t"))

    self.expect_google_login()

    config.pages[0].login.run_with(self.action_runner, self.run, page[0])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
