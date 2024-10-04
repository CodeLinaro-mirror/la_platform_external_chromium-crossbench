# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import contextlib
import datetime as dt
import io
import logging
import pathlib
from typing import Final, List, Optional, Sequence, Tuple
from unittest import mock

import crossbench
from crossbench import path as pth
from crossbench import plt
from crossbench.benchmarks.loading.loadline_presets import \
    LoadLineTabletBenchmark
from crossbench.browsers.browser import Browser
from crossbench.browsers.settings import Settings
from crossbench.cli.cli import CrossBenchCLI
from crossbench.cli.config.browser_variants import BrowserVariantsConfig
from crossbench.cli.config.network import NetworkConfig
from crossbench.cli.config.secrets import SecretsConfig
from pyfakefs import fake_filesystem_unittest
from tests import test_helper
from tests.crossbench import mock_browser
from tests.crossbench.mock_helper import MockCLI, MockPlatform


class CrossbenchFakeFsTestCase(
    fake_filesystem_unittest.TestCase, metaclass=abc.ABCMeta):

  def setUp(self) -> None:
    super().setUp()
    self.setUpPyfakefs(modules_to_reload=[crossbench, mock_browser, pth])
    # gettext is used extensively in argparse
    gettext_patcher = mock.patch(
        "gettext.dgettext", side_effect=lambda domain, message: message)
    gettext_patcher.start()
    self.addCleanup(gettext_patcher.stop)

    sleep_patcher = mock.patch('time.sleep', return_value=None)
    sleep_patcher.start()
    self.addCleanup(sleep_patcher.stop)

  def create_file(self,
                  path_str: str,
                  contents: Optional[str] = None) -> pathlib.Path:
    path = pathlib.Path(path_str)
    self.fs.create_file(path, contents=contents)
    return path


class BaseCrossbenchTestCase(CrossbenchFakeFsTestCase, metaclass=abc.ABCMeta):

  def filter_splashscreen_urls(self, urls: Sequence[str]) -> List[str]:
    return [url for url in urls if not url.startswith("data:")]

  def setUp(self) -> None:
    # Instantiate MockPlatform before setting up fake_filesystem so we can
    # still interact with the original, real plt.Platform object for extracting
    # basic system information.
    self.platform = MockPlatform()  # pytype: disable=not-instantiable
    super().setUp()
    self._default_log_level = logging.getLogger().getEffectiveLevel()
    logging.getLogger().setLevel(logging.CRITICAL)
    for mock_browser_cls in mock_browser.ALL:
      mock_browser_cls.setup_fs(self.fs)
      self.assertTrue(mock_browser_cls.mock_app_path().exists())
    self.out_dir = pathlib.Path("/tmp/results/test")
    self.out_dir.parent.mkdir(parents=True)
    self.fs.add_real_directory(
        LoadLineTabletBenchmark.default_network_config_path().parent,
        lazy_read=(not test_helper.is_google_env()))
    if test_helper.is_google_env():
      self.fs.add_real_directory("/build/cas")
    self.browsers: List[mock_browser.MockBrowser] = [
        mock_browser.MockChromeDev(
            "dev", settings=Settings(platform=self.platform)),
        mock_browser.MockChromeStable(
            "stable", settings=Settings(platform=self.platform))
    ]
    mock_platform_patcher = mock.patch.object(plt, "PLATFORM", self.platform)
    mock_platform_patcher.start()
    self.addCleanup(mock_platform_patcher.stop)
    for browser in self.browsers:
      self.assertListEqual(browser.expected_js, [])
    self.mock_args = mock.Mock(
        wraps=False,
        driver_path=None,
        network_config=None,
        browser_config=None,
        viewport=None,
        splash_screen=None,
        secrets=SecretsConfig(),
        wipe_system_user_data=False,
        http_request_timeout=dt.timedelta(),
        cache_dir=pathlib.Path("test_cache_dir"),
        enable_features=None,
        disable_features=None,
        js_flags=None,
        enable_field_trial_config=False,
        network=NetworkConfig.default(),
        probe=[],
        other_browser_args=[],
        driver_logging=False)

  def tearDown(self) -> None:
    logging.getLogger().setLevel(self._default_log_level)
    self.assertListEqual(self.platform.sh_results, [])
    super().tearDown()


class SysExitTestException(Exception):

  def __init__(self, exit_code=0):
    super().__init__("sys.exit")
    self.exit_code = exit_code


class BaseCliTestCase(BaseCrossbenchTestCase):

  SPLASH_URLS_LEN: Final[int] = 2

  def setUp(self) -> None:
    super().setUp()

    # tabulate and textwrap can be slow for tests, let's mock them out.
    def mock_tabulate(table, *args, **kwargs):
      del args, kwargs
      return str(table)

    patcher = mock.patch("tabulate.tabulate", side_effect=mock_tabulate)
    self.addCleanup(patcher.stop)
    patcher.start()

    def mock_wrap(text, *args, **kwargs):
      del args, kwargs
      return [text]

    patcher = mock.patch("textwrap.wrap", side_effect=mock_wrap)
    self.addCleanup(patcher.stop)
    patcher.start()

  def run_cli_output(self,
                     *args,
                     raises=None,
                     enable_logging: bool = True) -> Tuple[MockCLI, str, str]:
    with mock.patch(
        "sys.stdout", new_callable=io.StringIO) as mock_stdout, mock.patch(
            "sys.stderr", new_callable=io.StringIO) as mock_stderr:
      cli = self.run_cli(*args, raises=raises, enable_logging=enable_logging)
    stdout = mock_stdout.getvalue()
    stderr = mock_stderr.getvalue()
    # Make sure we don't accidentally reuse the buffers across run_cli calls.
    mock_stdout.close()
    mock_stderr.close()
    return cli, stdout, stderr

  def run_cli(self,
              *args,
              raises=None,
              enable_logging: bool = False) -> MockCLI:
    cli = MockCLI(platform=self.platform, enable_logging=enable_logging)
    with mock.patch(
        "sys.exit", side_effect=SysExitTestException), mock.patch.object(
            plt, "PLATFORM", self.platform):
      if raises:
        with self.assertRaises(raises):
          cli.run(args)
      else:
        cli.run(args)
    return cli

  def mock_chrome_stable(self):
    return mock.patch.object(
        BrowserVariantsConfig,
        "_get_browser_cls",
        return_value=mock_browser.MockChromeStable)

  @contextlib.contextmanager
  def patch_get_browser(self, return_value: Optional[Sequence[Browser]] = None):
    if not return_value:
      return_value = self.browsers
    with mock.patch.object(
        CrossBenchCLI, "_get_browsers", return_value=return_value):
      yield
