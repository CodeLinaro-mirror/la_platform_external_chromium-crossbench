# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt
from unittest import mock

from typing_extensions import override

from crossbench.action_runner.action.enums import WindowTarget
from crossbench.benchmarks.web_power.base import WebPowerSiteConfig
from crossbench.benchmarks.web_power.page_load import \
    WebPowerPageLoadBenchmark, WebPowerPageLoadStory
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.benchmarks.web_power.test_base import \
    BaseWebPowerBenchmarkTestCase


class WebPowerPageLoadStoryTestCase(BaseCrossbenchTestCase):

  def test_instantiate_default_youtube(self) -> None:
    story = WebPowerPageLoadStory(
        name_suffix="youtube",
        site_config=WebPowerSiteConfig(url="https://youtube.com"),
    )
    self.assertEqual(story.url, "https://youtube.com")
    self.assertEqual(story.page_load_count, story.DEFAULT_PAGE_LOAD_COUNT)
    self.assertEqual(story.interval, story.DEFAULT_INTERVAL)

  def test_instantiate_default_cnn(self) -> None:
    story = WebPowerPageLoadStory(
        name_suffix="cnn",
        site_config=WebPowerSiteConfig(url="https://cnn.com"),
    )
    self.assertEqual(story.page_load_count, story.DEFAULT_CNN_PAGE_LOAD_COUNT)

  def test_instantiate_custom(self) -> None:
    interval = dt.timedelta(seconds=5)
    story = WebPowerPageLoadStory(
        name_suffix="cnn",
        site_config=WebPowerSiteConfig(url="https://www.cnn.com"),
        page_load_count=5,
        interval=interval,
    )
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.page_load_count, 5)
    self.assertEqual(story.interval, interval)

  def test_setup_window_target(self) -> None:
    story = WebPowerPageLoadStory(
        name_suffix="test",
        site_config=WebPowerSiteConfig(url="https://test.com"),
    )
    mock_run = self.mock_run()

    with mock.patch.object(mock_run.browser, "show_url") as mock_show_url:
      story.setup(mock_run)
      mock_show_url.assert_called_once_with(
          "https://test.com", target=WindowTarget.NEW_TAB)

  def test_run_tab_count(self) -> None:
    story = WebPowerPageLoadStory(
        name_suffix="test",
        site_config=WebPowerSiteConfig(url="https://test.com"),
        page_load_count=5,
    )
    mock_run = self.mock_run()

    class TabTracker:

      def __init__(self, test_case: WebPowerPageLoadStoryTestCase):
        self.test_case = test_case
        self.tabs = 1

      def show_url(self, url, target=WindowTarget.SELF, **kwargs):
        if target == WindowTarget.NEW_TAB:
          self.tabs += 1
        self.test_case.assertLessEqual(self.tabs, 2)

      def close_tab(self, *args, **kwargs):
        self.tabs -= 1

    tracker = TabTracker(self)

    with (
        mock.patch.object(
            mock_run.browser, "show_url", side_effect=tracker.show_url),
        mock.patch.object(
            mock_run.browser, "close_tab", side_effect=tracker.close_tab),
        mock.patch.object(mock_run.browser, "clear_cache"),
    ):
      story.setup(mock_run)
      story.run(mock_run)

    self.assertEqual(tracker.tabs, 2)


class WebPowerPageLoadBenchmarkTestCase(BaseWebPowerBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self) -> type[WebPowerPageLoadBenchmark]:
    return WebPowerPageLoadBenchmark

  def test_kwargs_from_cli_defaults(self) -> None:
    args = self.parse_args("--site", "cnn")
    kwargs = WebPowerPageLoadBenchmark.kwargs_from_cli(args)
    [story] = kwargs["stories"]
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.page_load_count,
                     WebPowerPageLoadStory.DEFAULT_CNN_PAGE_LOAD_COUNT)
    self.assertEqual(story.interval, WebPowerPageLoadStory.DEFAULT_INTERVAL)
    self.assertEqual(story.stabilization_time,
                     story.site_config.default_stabilization_time)

  def test_kwargs_from_cli_custom(self) -> None:
    args = self.parse_args(
        "--site=cnn",
        "--page-loads=15",
        "--interval=10s",
        "--stabilization-time=15s",
    )
    kwargs = WebPowerPageLoadBenchmark.kwargs_from_cli(args)
    [story] = kwargs["stories"]
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.page_load_count, 15)
    self.assertEqual(story.interval, dt.timedelta(seconds=10))
    self.assertEqual(story.stabilization_time, dt.timedelta(seconds=15))

  def test_kwargs_from_cli_aliases(self) -> None:
    args = self.parse_args(
        "--site=cnn",
        "--page-load-count=12",
        "--interval=6s",
    )
    kwargs = WebPowerPageLoadBenchmark.kwargs_from_cli(args)
    [story] = kwargs["stories"]
    self.assertEqual(story.page_load_count, 12)
    self.assertEqual(story.interval, dt.timedelta(seconds=6))

  def test_kwargs_from_cli_page_loads_invalid(self) -> None:
    with self.assertRaisesRegex(argparse.ArgumentError, "--page-loads"):
      self.parse_args("--page-loads=-1")
    with self.assertRaisesRegex(argparse.ArgumentError, "--page-loads"):
      self.parse_args("--page-loads=0")
    with self.assertRaisesRegex(argparse.ArgumentError, "--page-loads"):
      self.parse_args("--page-loads=foo")
    with self.assertRaisesRegex(argparse.ArgumentError, "--page-load-count"):
      self.parse_args("--page-load-count=-1")
    with self.assertRaisesRegex(argparse.ArgumentError, "--page-load-count"):
      self.parse_args("--page-load-count=0")
    with self.assertRaisesRegex(argparse.ArgumentError, "--page-load-count"):
      self.parse_args("--page-load-count=foo")

  def test_kwargs_from_cli_interval_invalid(self) -> None:
    with self.assertRaisesRegex(argparse.ArgumentError, "--interval"):
      self.parse_args("--interval=-1s")
    with self.assertRaisesRegex(argparse.ArgumentError, "--interval"):
      self.parse_args("--interval=0s")
    with self.assertRaisesRegex(argparse.ArgumentError, "--interval"):
      self.parse_args("--interval=foo")

  def test_from_cli_args(self) -> None:
    args = self.parse_args(
        "--site=cnn",
        "--page-loads=7",
        "--interval=4s",
    )
    benchmark = WebPowerPageLoadBenchmark.from_cli_args(args)
    self.assertEqual(len(benchmark.stories), 1)
    story = benchmark.stories[0]
    self.assertIsInstance(story, WebPowerPageLoadStory)
    self.assertEqual(story.page_load_count, 7)
    self.assertEqual(story.interval, dt.timedelta(seconds=4))



if __name__ == "__main__":
  test_helper.run_pytest(__file__)
