# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import argparse
import contextlib
import datetime as dt
import io
import logging
import pathlib
from typing import TYPE_CHECKING, Final, Optional, Sequence, Type
from unittest import mock

from pyfakefs import fake_filesystem_unittest
from typing_extensions import override

import crossbench
from crossbench import path as pth
from crossbench import plt
from crossbench.action_runner.action.wait_for_ready_state import \
    WaitForReadyStateAction
from crossbench.benchmarks.loading.playback_controller import \
    PlaybackController
from crossbench.benchmarks.loading.tab_controller import TabController
from crossbench.benchmarks.loadline import (LoadLine1TabletBenchmark,
                                            LoadLine2TabletBenchmark)
from crossbench.browsers.settings import Settings
from crossbench.cli.config.browser_variants import BaseBrowserVariantsConfig
from crossbench.cli.config.env import EnvConfig
from crossbench.cli.config.network import NetworkConfig
from crossbench.cli.config.secrets import Secrets
from crossbench.cli.subcommand.benchmark import BenchmarkSubcommand
from crossbench.helper.wake_lock import WakeLock
from crossbench.runner.runner import Runner
from tests import test_helper
from tests.crossbench import mock_browser
from tests.crossbench.mock_helper import MockCLI, MockPlatform

if TYPE_CHECKING:
  from crossbench.browsers.browser import Browser


class CrossbenchFakeFsTestCase(
    fake_filesystem_unittest.TestCase, metaclass=abc.ABCMeta):

  def setUp(self) -> None:
    super().setUp()
    self.setUpPyfakefs(modules_to_reload=[crossbench, mock_browser, pth, plt])
    # gettext is used extensively in argparse
    gettext_patcher = mock.patch(
        "gettext.dgettext", side_effect=lambda domain, message: message)
    gettext_patcher.start()
    self.addCleanup(gettext_patcher.stop)

    sleep_patcher = mock.patch("time.sleep", return_value=None)
    self.sleep_mock = sleep_patcher.start()
    self.addCleanup(sleep_patcher.stop)
    # This is platform specific and causes issues pending sh commands
    self.sleep_preventer_patcher = mock.patch.object(WakeLock, "__enter__")
    self.addCleanup(self.sleep_preventer_patcher.stop)
    self.sleep_preventer_patcher.start()


  def create_file(self, path_str: str, contents: str = "") -> pathlib.Path:
    path = pathlib.Path(path_str)
    self.fs.create_file(path, contents=contents)
    return path


TEST_WARNING = "Test Warning"


class CrossbenchMockArgsMixin:

  def mock_args(self, **kwargs) -> argparse.Namespace:
    args = argparse.Namespace(
        wraps=kwargs.pop("wraps", False),
        throw=kwargs.pop("throw", False),
        browser=kwargs.pop("browser", []),
        driver_path=kwargs.pop("driver_path", None),
        remote_driver_path=kwargs.pop("remote_driver_path", None),
        network_config=kwargs.pop("network_config", None),
        browser_config=kwargs.pop("browser_config", None),
        probe_config=kwargs.pop("probe_config", None),
        viewport=kwargs.pop("viewport", None),
        splash_screen=kwargs.pop("splash_screen", None),
        secrets=kwargs.pop("secrets", Secrets()),
        driver_logging=kwargs.pop("driver_logging", False),
        wipe_system_user_data=kwargs.pop("wipe_system_user_data", False),
        http_request_timeout=kwargs.pop("", dt.timedelta()),
        cache_dir=pathlib.Path("test_cache_dir"),
        browser_cache_dir=kwargs.pop("browser_cache_dir", None),
        clear_browser_cache_dir=kwargs.pop("clear_browser_cache_dir", None),
        enable_features=kwargs.pop("enable_features", None),
        disable_features=kwargs.pop("disable_features", None),
        js_flags=kwargs.pop("js_flags", None),
        sandbox=kwargs.pop("sandbox", None),
        enable_field_trial_config=kwargs.pop("enable_field_trial_config", None),
        network=kwargs.pop("network", NetworkConfig.default()),
        probe=kwargs.pop("probe", []),
        other_browser_args=kwargs.pop("other_browser_args", []),
        playback=kwargs.pop("playback", PlaybackController.default()),
        tabs=kwargs.pop("tabs", TabController.default()),
        about_blank_duration=kwargs.pop("about_blank_duration", dt.timedelta()),
        run_login=kwargs.pop("run_login", True),
        run_setup=kwargs.pop("run_setup", True),
        env=EnvConfig.default(),
        action_runner_config=kwargs.pop("action_runner_config", None))
    assert not kwargs, f"got unused kwargs: {kwargs}"
    return args


class BaseCrossbenchTestCase(
    CrossbenchMockArgsMixin, CrossbenchFakeFsTestCase, metaclass=abc.ABCMeta):

  def filter_splashscreen_urls(self, urls: Sequence[str]) -> list[str]:
    return [url for url in urls if not url.startswith("data:")]

  @override
  def setUp(self) -> None:
    # Instantiate MockPlatform before setting up fake_filesystem so we can
    # still interact with the original, real plt.Platform object for extracting
    # basic system information.
    self.platform = MockPlatform()  # pytype: disable=not-instantiable
    self.platform.use_fs = True
    super().setUp()
    self._default_log_level = logging.getLogger().getEffectiveLevel()
    logging.getLogger().setLevel(logging.CRITICAL)
    for mock_browser_cls in mock_browser.ALL:
      mock_browser_cls.setup_fs(self.fs)
      self.assertTrue(mock_browser_cls.mock_app_path(self.platform).exists())
    self.out_dir = pathlib.Path("/tmp/results/test")
    self.out_dir.parent.mkdir(parents=True)
    self.browsers: list[mock_browser.MockBrowser] = [
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

  def setup_loadline_configs(self):
    self.setup_config_dir(
        LoadLine1TabletBenchmark.default_network_config_path().parent)
    self.setup_config_dir(
        LoadLine2TabletBenchmark.default_network_config_path().parent)

  def setup_config_dir(self, config_dir):
    self.fs.add_real_directory(
        config_dir,
        lazy_read=not test_helper.is_google_env())
    if test_helper.is_google_env():
      # On google3, all files have been replaced by symlinks. The link targets
      # must be added in order for these symlinks to resolve.
      for child in config_dir.glob("**/*"):
        if child.is_symlink():
          link_target = child.readlink()
          if not link_target.exists():
            self.fs.add_real_file(link_target)

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

  @override
  def setUp(self) -> None:
    super().setUp()

    # tabulate and textwrap can be slow for tests, let's mock them out.
    self.setup_tabulate_patcher()
    self.setup_wrap_patcher()

    self.setup_wait_for_ready_state_patcher()

    self.setup_loadline_configs()

  def setup_tabulate_patcher(self) -> None:
    def mock_tabulate(table, *args, **kwargs):
      del args, kwargs
      return str(table)

    patcher = mock.patch("tabulate.tabulate", side_effect=mock_tabulate)
    self.addCleanup(patcher.stop)
    patcher.start()

  def setup_wrap_patcher(self) -> None:
    def mock_wrap(text, *args, **kwargs):
      del args, kwargs
      return [text]

    patcher = mock.patch("textwrap.wrap", side_effect=mock_wrap)
    self.addCleanup(patcher.stop)
    patcher.start()

  def setup_wait_for_ready_state_patcher(self):
    patcher = mock.patch.object(
        WaitForReadyStateAction, "run_with", return_value=True)
    self.addCleanup(patcher.stop)
    patcher.start()

  def run_cli_output(self,
                     *args,
                     raises=None,
                     enable_logging: bool = True) -> tuple[MockCLI, str, str]:
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

  @contextlib.contextmanager
  def _patch_get_runner(self):
    with mock.patch.object(
        BenchmarkSubcommand, "_get_runner", side_effect=self._mock_get_runner):
      yield

  def _mock_get_runner(self, args, benchmark, env_config, env_validation_mode,
                       timing):
    if not args.out_dir:
      # Use stable mock out dir
      args.out_dir = pathlib.Path("/results")
      assert not args.out_dir.exists()
    runner_kwargs = Runner.kwargs_from_cli(args)
    runner = Runner(
        benchmark=benchmark,
        env_config=env_config,
        env_validation_mode=env_validation_mode,
        timing=timing,
        **runner_kwargs,
        # Use custom platform
        platform=self.platform,
        in_memory_result_db=True)
    return runner

  @contextlib.contextmanager
  def _patch_sys_exit(self):
    with mock.patch(
        "sys.exit", side_effect=SysExitTestException), mock.patch.object(
            plt, "PLATFORM", self.platform):
      yield

  @contextlib.contextmanager
  def _patch_get_browser_cls(self,
                             return_value: Optional[Type[Browser]] = None,
                             **kwargs):
    if not kwargs:
      kwargs["return_value"] = return_value or mock_browser.MockChromeStable
    with mock.patch.object(BaseBrowserVariantsConfig, "get_browser_cls",
                           **kwargs) as patcher:
      yield patcher

  def run_cli(self,
              *args,
              raises=None,
              enable_logging: bool = False) -> MockCLI:
    cli = MockCLI(platform=self.platform, enable_logging=enable_logging)
    with self._patch_sys_exit(), self._patch_get_runner():
      if raises:
        with self.assertRaises(raises):
          cli.run(args)
      else:
        cli.run(args)
    return cli

  @contextlib.contextmanager
  def _patch_get_browser(self,
                         return_value: Optional[Sequence[Browser]] = None):
    if not return_value:
      return_value = self.browsers
    with mock.patch.object(
        BenchmarkSubcommand, "_get_browsers", return_value=return_value):
      yield
