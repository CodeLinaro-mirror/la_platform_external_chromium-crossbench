# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt

from typing_extensions import override

from crossbench.benchmarks.web_power.base import WebPowerSiteConfig
from crossbench.benchmarks.web_power.scroll import WebPowerScrollBenchmark, \
    WebPowerScrollStory
from crossbench.cli.parser import CBArgumentParser
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.benchmarks.helper import BaseBenchmarkTestCase


class WebPowerScrollStoryTestCase(BaseCrossbenchTestCase):

  def test_instantiate_default(self) -> None:
    story = WebPowerScrollStory(
        name_suffix="test",
        site_config=WebPowerSiteConfig(url="https://www.cnn.com"),
    )
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.scroll_count, story.DEFAULT_SCROLL_COUNT)
    self.assertEqual(story.input_rate, story.DEFAULT_INPUT_RATE)

  def test_instantiate_custom(self) -> None:
    story = WebPowerScrollStory(
        name_suffix="test",
        site_config=WebPowerSiteConfig(url="https://www.cnn.com"),
        scroll_count=10,
        input_rate=120,
    )
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.scroll_count, 10)
    self.assertEqual(story.input_rate, 120)


class WebPowerScrollBenchmarkTestCase(BaseBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self) -> type[WebPowerScrollBenchmark]:
    return WebPowerScrollBenchmark

  def test_kwargs_from_cli_defaults(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerScrollBenchmark.add_cli_arguments(parser)
    args = parser.parse_args(["--site", "cnn"])
    kwargs = WebPowerScrollBenchmark.kwargs_from_cli(args)
    self.assertEqual(len(kwargs["stories"]), 1)
    story = kwargs["stories"][0]
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.scroll_count,
                     WebPowerScrollStory.DEFAULT_SCROLL_COUNT)
    self.assertEqual(story.input_rate, WebPowerScrollStory.DEFAULT_INPUT_RATE)
    self.assertEqual(story.stabilization_time,
                     story.site_config.default_stabilization_time)

  def test_kwargs_from_cli_custom(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerScrollBenchmark.add_cli_arguments(parser)
    args = parser.parse_args([
        "--site=cnn",
        "--scrolls=12",
        "--input-rate=100",
        "--stabilization-time=15s",
    ])
    kwargs = WebPowerScrollBenchmark.kwargs_from_cli(args)
    self.assertEqual(len(kwargs["stories"]), 1)
    story = kwargs["stories"][0]
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.scroll_count, 12)
    self.assertEqual(story.input_rate, 100)
    self.assertEqual(story.stabilization_time, dt.timedelta(seconds=15))

  def test_kwargs_from_cli_invalid(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerScrollBenchmark.add_cli_arguments(parser)
    with self.assertRaises(argparse.ArgumentError):
      parser.parse_args(["--scrolls=-1"])
    with self.assertRaises(argparse.ArgumentError):
      parser.parse_args(["--scrolls=0"])
    with self.assertRaises(argparse.ArgumentError):
      parser.parse_args(["--scrolls=foo"])
    with self.assertRaises(argparse.ArgumentError):
      parser.parse_args(["--input-rate=-100"])
    with self.assertRaises(argparse.ArgumentError):
      parser.parse_args(["--input-rate=0"])
    with self.assertRaises(argparse.ArgumentError):
      parser.parse_args(["--input-rate=bar"])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
