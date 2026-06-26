# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt

from typing_extensions import override

from crossbench.benchmarks.web_power.base import WebPowerSiteConfig
from crossbench.benchmarks.web_power.page_load import \
    WebPowerPageLoadBenchmark, WebPowerPageLoadStory
from crossbench.cli.parser import CBArgumentParser
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.benchmarks.helper import BaseBenchmarkTestCase


class WebPowerPageLoadStoryTestCase(BaseCrossbenchTestCase):

  def test_instantiate_default_youtube(self) -> None:
    story = WebPowerPageLoadStory(
        name_suffix="youtube",
        site_config=WebPowerSiteConfig(url="https://youtube.com"),
    )
    self.assertEqual(story.url, "https://youtube.com")
    self.assertEqual(story.page_load_count, story.DEFAULT_PAGE_LOAD_COUNT)
    self.assertEqual(story.interval, story.DEFAULT_INTERVAL)
    self.assertEqual(story.lead_wait_time, story.DEFAULT_LEAD_WAIT_TIME)
    self.assertEqual(story.cool_off_time, story.DEFAULT_COOL_OFF_TIME)

  def test_instantiate_default_cnn(self) -> None:
    story = WebPowerPageLoadStory(
        name_suffix="cnn",
        site_config=WebPowerSiteConfig(url="https://cnn.com"),
    )
    self.assertEqual(story.page_load_count, story.DEFAULT_CNN_PAGE_LOAD_COUNT)

  def test_instantiate_custom(self) -> None:
    interval = dt.timedelta(seconds=5)
    lead_wait = dt.timedelta(seconds=15)
    cool_off = dt.timedelta(seconds=30)
    story = WebPowerPageLoadStory(
        name_suffix="cnn",
        site_config=WebPowerSiteConfig(url="https://www.cnn.com"),
        page_load_count=5,
        interval=interval,
        lead_wait_time=lead_wait,
        cool_off_time=cool_off,
    )
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.page_load_count, 5)
    self.assertEqual(story.interval, interval)
    self.assertEqual(story.lead_wait_time, lead_wait)
    self.assertEqual(story.cool_off_time, cool_off)


class WebPowerPageLoadBenchmarkTestCase(BaseBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self) -> type[WebPowerPageLoadBenchmark]:
    return WebPowerPageLoadBenchmark

  def test_kwargs_from_cli_defaults(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerPageLoadBenchmark.add_cli_arguments(parser)
    args = parser.parse_args(["--site", "cnn"])
    kwargs = WebPowerPageLoadBenchmark.kwargs_from_cli(args)
    self.assertEqual(len(kwargs["stories"]), 1)
    story = kwargs["stories"][0]
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.page_load_count,
                     WebPowerPageLoadStory.DEFAULT_CNN_PAGE_LOAD_COUNT)
    self.assertEqual(story.interval, WebPowerPageLoadStory.DEFAULT_INTERVAL)
    self.assertEqual(story.lead_wait_time,
                     WebPowerPageLoadStory.DEFAULT_LEAD_WAIT_TIME)
    self.assertEqual(story.cool_off_time,
                     WebPowerPageLoadStory.DEFAULT_COOL_OFF_TIME)

  def test_kwargs_from_cli_custom(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerPageLoadBenchmark.add_cli_arguments(parser)
    args = parser.parse_args([
        "--site=cnn",
        "--page-loads=15",
        "--interval=10s",
        "--lead-wait-time=5s",
        "--cool-off-time=30s",
    ])
    kwargs = WebPowerPageLoadBenchmark.kwargs_from_cli(args)
    self.assertEqual(len(kwargs["stories"]), 1)
    story = kwargs["stories"][0]
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.page_load_count, 15)
    self.assertEqual(story.interval, dt.timedelta(seconds=10))
    self.assertEqual(story.lead_wait_time, dt.timedelta(seconds=5))
    self.assertEqual(story.cool_off_time, dt.timedelta(seconds=30))

  def test_kwargs_from_cli_invalid(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerPageLoadBenchmark.add_cli_arguments(parser)
    with self.assertRaises(argparse.ArgumentError):
      parser.parse_args(["--page-loads=-1"])
    with self.assertRaises(argparse.ArgumentError):
      parser.parse_args(["--page-loads=0"])
    with self.assertRaises(argparse.ArgumentError):
      parser.parse_args(["--page-loads=foo"])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
