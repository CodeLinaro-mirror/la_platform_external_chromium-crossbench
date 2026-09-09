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
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.benchmarks.web_power.test_base import \
    BaseWebPowerBenchmarkTestCase


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


class WebPowerScrollBenchmarkTestCase(BaseWebPowerBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self) -> type[WebPowerScrollBenchmark]:
    return WebPowerScrollBenchmark

  def test_kwargs_from_cli_defaults(self) -> None:
    args = self.parse_args("--site", "cnn")
    kwargs = WebPowerScrollBenchmark.kwargs_from_cli(args)
    [story] = kwargs["stories"]
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.scroll_count,
                     WebPowerScrollStory.DEFAULT_SCROLL_COUNT)
    self.assertEqual(story.input_rate, WebPowerScrollStory.DEFAULT_INPUT_RATE)
    self.assertEqual(story.stabilization_time,
                     story.site_config.default_stabilization_time)

  def test_kwargs_from_cli_custom(self) -> None:
    args = self.parse_args(
        "--site=cnn",
        "--scrolls=12",
        "--input-rate=100",
        "--stabilization-time=15s",
    )
    kwargs = WebPowerScrollBenchmark.kwargs_from_cli(args)
    [story] = kwargs["stories"]
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story.scroll_count, 12)
    self.assertEqual(story.input_rate, 100)
    self.assertEqual(story.stabilization_time, dt.timedelta(seconds=15))

  def test_kwargs_from_cli_aliases(self) -> None:
    args = self.parse_args(
        "--site=cnn",
        "--scroll-count=15",
        "--rate=90",
    )
    kwargs = WebPowerScrollBenchmark.kwargs_from_cli(args)
    [story] = kwargs["stories"]
    self.assertEqual(story.scroll_count, 15)
    self.assertEqual(story.input_rate, 90)

  def test_kwargs_from_cli_scrolls_invalid(self) -> None:
    with self.assertRaisesRegex(argparse.ArgumentError, "--scrolls"):
      self.parse_args("--scrolls=-1")
    with self.assertRaisesRegex(argparse.ArgumentError, "--scrolls"):
      self.parse_args("--scrolls=0")
    with self.assertRaisesRegex(argparse.ArgumentError, "--scrolls"):
      self.parse_args("--scrolls=foo")
    with self.assertRaisesRegex(argparse.ArgumentError, "--scroll-count"):
      self.parse_args("--scroll-count=-1")
    with self.assertRaisesRegex(argparse.ArgumentError, "--scroll-count"):
      self.parse_args("--scroll-count=0")
    with self.assertRaisesRegex(argparse.ArgumentError, "--scroll-count"):
      self.parse_args("--scroll-count=foo")

  def test_kwargs_from_cli_input_rate_invalid(self) -> None:
    with self.assertRaisesRegex(argparse.ArgumentError, "--input-rate"):
      self.parse_args("--input-rate=-100")
    with self.assertRaisesRegex(argparse.ArgumentError, "--input-rate"):
      self.parse_args("--input-rate=0")
    with self.assertRaisesRegex(argparse.ArgumentError, "--input-rate"):
      self.parse_args("--input-rate=bar")
    with self.assertRaisesRegex(argparse.ArgumentError, "--rate"):
      self.parse_args("--rate=-100")
    with self.assertRaisesRegex(argparse.ArgumentError, "--rate"):
      self.parse_args("--rate=0")
    with self.assertRaisesRegex(argparse.ArgumentError, "--rate"):
      self.parse_args("--rate=bar")

  def test_from_cli_args(self) -> None:
    args = self.parse_args(
        "--site=cnn",
        "--scroll-count=8",
        "--rate=60",
    )
    benchmark = WebPowerScrollBenchmark.from_cli_args(args)
    self.assertEqual(len(benchmark.stories), 1)
    story = benchmark.stories[0]
    self.assertIsInstance(story, WebPowerScrollStory)
    self.assertEqual(story.scroll_count, 8)
    self.assertEqual(story.input_rate, 60)



if __name__ == "__main__":
  test_helper.run_pytest(__file__)
