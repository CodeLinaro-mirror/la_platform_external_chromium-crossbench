# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import contextlib
import io
import pathlib
from typing import List, Optional, Tuple
from unittest import mock

import pytest

import crossbench.browsers.all as browsers
from crossbench import plt
from crossbench.cli.cli import CrossBenchCLI
from tests import test_helper
from tests.test_helper import TestEnv


class SysExitException(Exception):

  def __init__(self):
    super().__init__("sys.exit")


@pytest.fixture(autouse=True)
def cli_test_context(request, browser_path, driver_path):
  if "skip_mock" in request.keywords:
    yield
    return
  # Mock out chrome's stable path to be able to run on the CQ with the
  # --test-browser-path option.
  with mock.patch(
      "crossbench.browsers.all.Chrome.stable_path", return_value=browser_path):
    if not driver_path:
      yield
    else:
      # The CQ uses the latest canary, which might not have a easily publicly
      # accessible chromedriver available.
      with mock.patch(("crossbench.browsers.chromium"
                       ".driver_finder.ChromeDriverFinder.download"),
                      return_value=driver_path):
        yield


def _run_cli(*args: str,
             extra_flags: tuple[str, ...] = (),
             test_env: Optional[TestEnv] = None,
             auto_headless: bool = False) -> Tuple[CrossBenchCLI, io.StringIO]:
  if test_env is not None:
    args += (f"--out-dir={test_env.results_dir}",) + test_env.cq_flags
  if auto_headless and not plt.PLATFORM.has_display:
    if "--headless" not in args:
      args += ("--headless",)
      args = tuple(arg for arg in args if not arg.startswith("--viewport="))
  args += extra_flags
  cli = CrossBenchCLI()
  with contextlib.redirect_stdout(io.StringIO()) as stdout:
    with mock.patch("sys.exit", side_effect=SysExitException):
      cli.run(args)
  return cli, stdout


def _get_browser_dirs(results_dir: pathlib.Path) -> List[pathlib.Path]:
  assert results_dir.is_dir()
  browser_dirs = [path for path in results_dir.iterdir() if path.is_dir()]
  return browser_dirs


def _get_v8_log_files(results_dir: pathlib.Path) -> List[pathlib.Path]:
  return list(results_dir.glob("**/*-v8.log"))


@pytest.mark.xdist_group("end2end-benchmark")
def test_speedometer_2_0(test_env: TestEnv) -> None:
  # - Speedometer 2.0
  # - Speedometer --iterations flag
  # - Tracing probe with inline args
  # - --browser-config
  with pytest.raises(SysExitException):
    _run_cli("speedometer_2.0", "--help")
  _run_cli("describe", "benchmark", "speedometer_2.0")
  browser_config = test_env.root_dir / "config/doc/browser.config.hjson"
  assert browser_config.is_file()
  _run_cli(
      "sp_2.0",
      f"--browser-config={browser_config}",
      "--iterations=2",
      "--stories=jQuery-TodoMVC",
      "--env-validation=skip",
      "--probe=tracing:{preset:'minimal'}",
      test_env=test_env,
      auto_headless=True)


@pytest.mark.xdist_group("end2end-benchmark")
def test_speedometer_2_1(test_env: TestEnv) -> None:
  # - Speedometer 2.1
  # - Story filtering with regexp
  # - V8 probes
  # - minimal splashscreen
  # - inline probe arguments
  with pytest.raises(SysExitException):
    _run_cli("speedometer_2.1", "--help")
  _run_cli("describe", "benchmark", "speedometer_2.1")
  _run_cli(
      "sp2.1",
      "--browser=chrome-stable",
      "--splashscreen=minimal",
      "--iterations=2",
      "--env-validation=skip",
      "--stories=.*Vanilla.*",
      # V8 --prof doesn't always work on linux, skip it.
      "--probe=v8.log:"
      "{log_all:false, js_flags:['--log-maps'], prof:false, profview:false}",
      "--probe=v8.turbolizer",
      "--debug",
      test_env=test_env,
      auto_headless=True)

  browser_dirs = _get_browser_dirs(test_env.results_dir)
  assert len(browser_dirs) == 1
  v8_log_files = _get_v8_log_files(test_env.results_dir)
  assert len(v8_log_files) > 1


@pytest.mark.skip_mock
@pytest.mark.flaky(retries=3, delay=5)
def test_speedometer_2_1_custom_chrome_download(test_env: TestEnv) -> None:
  # - Custom chrome version downloads
  # - headless
  # Flaky due to downloading live custom builds.
  # TODO: speed up --browser=chrome-M111 and add it.
  _run_cli(
      "sp2.1",
      "--browser=chrome-M113",
      "--browser=chrome-111.0.5563.110",
      "--headless",
      "--iterations=1",
      "--env-validation=skip",
      "--stories=.*Vanilla.*",
      "--debug",
      test_env=test_env)

  browser_dirs = _get_browser_dirs(test_env.results_dir)
  assert len(browser_dirs) == 2
  v8_log_files = _get_v8_log_files(test_env.results_dir)
  assert not v8_log_files


@pytest.mark.skipif(
    not plt.PLATFORM.is_macos, reason="Safari is only available on macos")
@pytest.mark.xdist_group("end2end-benchmark")
def test_speedometer_2_1_chrome_safari(test_env: TestEnv, driver_path) -> None:
  # - Speedometer 3
  # - Merging stories over multiple iterations and browsers
  # - Testing safari
  # - --verbose flag
  # - no splashscreen
  # This fails on the CQ bot, so make sure we skip it there:
  if driver_path:
    pytest.skip("Skipping test on CQ.")
  platform = plt.PLATFORM
  if not platform.is_macos and (not platform.exists(
      browsers.Safari.default_path(platform))):
    pytest.skip("Test requires Safari, skipping on non macOS devices.")
  _run_cli(
      "sp2.1",
      "--browser=chrome",
      "--browser=safari",
      "--splashscreen=none",
      "--iterations=1",
      "--repeat=2",
      "--env-validation=skip",
      "--verbose",
      "--stories=.*React.*",
      test_env=test_env,
      auto_headless=True)

  browser_dirs = _get_browser_dirs(test_env.results_dir)
  assert len(browser_dirs) == 2
  v8_log_files = _get_v8_log_files(test_env.results_dir)
  assert not v8_log_files


@pytest.mark.xdist_group("end2end-benchmark")
def test_jetstream_2_0(test_env: TestEnv) -> None:
  # - jetstream 2.0
  # - merge / run separate stories
  # - custom multiple --js-flags
  # - custom viewport
  # - quiet flag
  with pytest.raises(SysExitException):
    _run_cli("jetstream_2.0", "--help")
  _run_cli("describe", "--json", "benchmark", "jetstream_2.0")
  _run_cli(
      "jetstream_2.0",
      "--browser=chrome-stable",
      "--separate",
      "--repeat=2",
      "--env-validation=skip",
      "--viewport=maximised",
      "--stories=.*date-format.*",
      "--quiet",
      "--js-flags=--log,--log-opt,--log-deopt",
      extra_flags=(
          "--",
          "--no-sandbox",
      ),
      test_env=test_env,
      auto_headless=True)

  browser_dirs = _get_browser_dirs(test_env.results_dir)
  assert len(browser_dirs) == 1


@pytest.mark.xdist_group("end2end-benchmark")
def test_jetstream_2_1(test_env: TestEnv) -> None:
  # - jetstream 2.1
  # - custom --time-unit
  # - explicit single story
  # - custom splashscreen
  # - custom viewport
  # - --probe-config
  with pytest.raises(SysExitException):
    _run_cli("jetstream_2.1", "--help")
  _run_cli("describe", "benchmark", "jetstream_2.1")
  probe_config = test_env.root_dir / "config/doc/probe.config.hjson"
  assert probe_config.is_file()
  chrome_version = "--browser=chrome"
  _run_cli(
      "jetstream_2.1",
      chrome_version,
      "--env-validation=skip",
      "--splashscreen=http://google.com",
      "--viewport=900x800",
      "--stories=Box2D",
      "--time-unit=0.9",
      f"--probe-config={probe_config}",
      "--throw",
      test_env=test_env,
      auto_headless=True)

  browser_dirs = _get_browser_dirs(test_env.results_dir)
  assert len(browser_dirs) == 1
  v8_log_files = _get_v8_log_files(test_env.results_dir)
  assert len(v8_log_files) > 1


@pytest.mark.xdist_group("end2end-benchmark")
def test_jetstream_2_2(test_env: TestEnv) -> None:
  # - jetstream 2.2
  # - custom --time-unit
  # - explicit single story
  # - custom splashscreen
  # - custom viewport
  # - --probe-config
  with pytest.raises(SysExitException):
    _run_cli("jetstream_2.2", "--help")
  _run_cli("describe", "benchmark", "jetstream_2.2")
  probe_config = test_env.root_dir / "config/doc/probe.config.hjson"
  assert probe_config.is_file()
  chrome_version = "--browser=chrome"
  _run_cli(
      "jetstream_2.2",
      chrome_version,
      "--env-validation=skip",
      "--splashscreen=http://google.com",
      "--viewport=900x800",
      "--stories=Box2D",
      "--time-unit=0.9",
      f"--probe-config={probe_config}",
      "--throw",
      test_env=test_env,
      auto_headless=True)

  browser_dirs = _get_browser_dirs(test_env.results_dir)
  assert len(browser_dirs) == 1
  v8_log_files = _get_v8_log_files(test_env.results_dir)
  assert len(v8_log_files) > 1


@pytest.mark.xdist_group("end2end-benchmark")
def test_loading(test_env: TestEnv) -> None:
  # - loading using named pages with timeouts
  # - custom cooldown time
  # - custom viewport
  # - performance.mark probe
  with pytest.raises(SysExitException):
    _run_cli("loading", "--help")
  _run_cli("describe", "benchmark", "loading")
  _run_cli(
      "loading",
      "--browser=chr",
      "--env-validation=skip",
      "--viewport=headless",
      "--stories=cnn",
      "--cool-down-time=2.5",
      "--probe=performance.entries",
      test_env=test_env,
      auto_headless=True)

  browser_dirs = _get_browser_dirs(test_env.results_dir)
  assert len(browser_dirs) == 1


@pytest.mark.skipif(
    plt.PLATFORM.is_win, reason="TODO(crbug.com/383896773): --page-config.")
def test_loading_page_config(test_env: TestEnv) -> None:
  # - loading with config file
  page_config = test_env.root_dir / "config/doc/page.config.hjson"
  assert page_config.is_file()
  _run_cli(
      "loading",
      "--env-validation=skip",
      f"--page-config={page_config}",
      "--probe=performance.entries",
      "--no-splash",
      "--cool-down-time=0",
      "--throw",
      test_env=test_env,
      auto_headless=True)


@pytest.mark.xdist_group("end2end-benchmark")
def test_loading_playback_urls(test_env: TestEnv) -> None:
  # - loading using url
  # - combined pages and --playback controller
  _run_cli(
      "loading",
      "--env-validation=skip",
      "--verbose-driver",
      "--playback=5.3s",
      "--viewport=fullscreen",
      "--stories=http://google.com,0.5,http://bing.com,0.4",
      "--probe=performance.entries",
      test_env=test_env,
      auto_headless=True)


@pytest.mark.xdist_group("end2end-benchmark")
def test_loading_playback(test_env: TestEnv) -> None:
  # - loading using named pages with timeouts
  # - separate pages and --playback controller
  # - viewport-size via chrome flag
  args = [
      "loading",
      "--browser=chr",
      "--env-validation=skip",
      "--playback=5.3s",
      "--separate",
      "--stories=twitter,2,facebook,0.4",
      "--probe=performance.entries",
  ]
  if not plt.PLATFORM.is_linux:
    args.extend([
        "--",
        "--window-size=900,500",
        "--window-position=150,150",
    ])
  _run_cli(*args, test_env=test_env, auto_headless=True)


@pytest.mark.skipif(
    not plt.PLATFORM.has_display, reason="Firefox cannot run headless")
@pytest.mark.xdist_group("end2end-benchmark")
def test_loading_playback_firefox(test_env: TestEnv) -> None:
  # - loading using named pages with timeouts
  # - --playback controller
  # - Firefox
  platform = plt.PLATFORM
  try:
    if not platform.exists(browsers.Firefox.default_path(platform)):
      pytest.skip("Test requires Firefox.")
  except Exception:  # pylint: disable=broad-exception-caught
    pytest.skip("Test requires Firefox.")
  _run_cli(
      "loading",
      "--browser=chr",
      "--browser=ff",
      "--env-validation=skip",
      "--playback=2x",
      "--stories=twitter,1,facebook,0.4",
      "--probe=performance.entries",
      test_env=test_env,
      auto_headless=True)

  browser_dirs = _get_browser_dirs(test_env.results_dir)
  assert len(browser_dirs) == 2


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
