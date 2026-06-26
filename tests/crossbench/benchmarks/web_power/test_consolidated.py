# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
from typing import Final

from typing_extensions import override

from crossbench.benchmarks.web_power.consolidated import WebPowerBenchmark, \
    WebPowerConsolidatedStoryFilter
from crossbench.benchmarks.web_power.idle import WebPowerIdleStory
from crossbench.benchmarks.web_power.media_playback import \
    WebPowerMediaPlaybackStory
from crossbench.benchmarks.web_power.page_load import WebPowerPageLoadStory
from crossbench.benchmarks.web_power.scroll import WebPowerScrollStory
from crossbench.benchmarks.web_power.volume_helper import VolumeMode
from crossbench.cli.parser import CBArgumentParser
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.benchmarks.helper import BaseBenchmarkTestCase


class WebPowerConsolidatedStoryFilterTestCase(BaseCrossbenchTestCase):

  def test_stories_from_names_explicit(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerBenchmark.add_cli_arguments(parser)
    args = parser.parse_args(
        ["--stories=idle-msn,scroll-cnn,media-playback-youtube"])
    story_filter = WebPowerConsolidatedStoryFilter.from_cli_args(
        WebPowerBenchmark.DEFAULT_STORY_CLS, args)
    stories = story_filter.stories

    self.assertEqual(len(stories), 3)
    self.assertEqual(stories[0].name, "web-power-idle-msn")
    self.assertEqual(stories[0].url, "https://msn.com/en-us")
    self.assertEqual(stories[1].name, "web-power-scroll-cnn")
    self.assertEqual(stories[1].url, "https://www.cnn.com")
    self.assertEqual(stories[2].name, "web-power-media-playback-youtube")
    self.assertEqual(stories[2].url,
                     "https://www.youtube.com/watch?v=XITHbsUUlYI")

  def test_stories_from_names_tag_idle(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerBenchmark.add_cli_arguments(parser)
    args = parser.parse_args(["--stories=#idle"])
    story_filter = WebPowerConsolidatedStoryFilter.from_cli_args(
        WebPowerBenchmark.DEFAULT_STORY_CLS, args)
    stories = story_filter.stories

    self.assertEqual(len(stories), 3)
    self.assertEqual(stories[0].name, "web-power-idle-ajnews")
    self.assertEqual(stories[1].name, "web-power-idle-cnn")
    self.assertEqual(stories[2].name, "web-power-idle-msn")

  def test_stories_from_names_tag_site(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerBenchmark.add_cli_arguments(parser)
    args = parser.parse_args(["--stories=#cnn"])
    story_filter = WebPowerConsolidatedStoryFilter.from_cli_args(
        WebPowerBenchmark.DEFAULT_STORY_CLS, args)
    stories = story_filter.stories

    self.assertEqual(len(stories), 3)
    self.assertEqual(stories[0].name, "web-power-idle-cnn")
    self.assertEqual(stories[1].name, "web-power-page-load-cnn")
    self.assertEqual(stories[2].name, "web-power-scroll-cnn")

  def _expected_canonical_stories(self) -> set[str]:
    return {
        "web-power-idle-msn",
        "web-power-idle-cnn",
        "web-power-idle-ajnews",
        "web-power-scroll-msn",
        "web-power-scroll-cnn",
        "web-power-scroll-ajnews",
        "web-power-page-load-msn",
        "web-power-page-load-cnn",
        "web-power-page-load-ajnews",
        "web-power-media-playback-youtube",
    }

  def test_stories_from_names_tag_canonical(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerBenchmark.add_cli_arguments(parser)
    args = parser.parse_args(["--stories=#canonical"])
    story_filter = WebPowerConsolidatedStoryFilter.from_cli_args(
        WebPowerBenchmark.DEFAULT_STORY_CLS, args)
    self.assertEqual({story.name for story in story_filter.stories},
                     self._expected_canonical_stories())

  def test_stories_from_names_default(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerBenchmark.add_cli_arguments(parser)
    args = parser.parse_args([])
    story_filter = WebPowerConsolidatedStoryFilter.from_cli_args(
        WebPowerBenchmark.DEFAULT_STORY_CLS, args)
    self.assertEqual({story.name for story in story_filter.stories},
                     self._expected_canonical_stories())


class WebPowerBenchmarkTestCase(BaseBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self) -> type[WebPowerBenchmark]:
    return WebPowerBenchmark

  def test_kwargs_from_cli_defaults(self) -> None:
    parser = WebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    kwargs = WebPowerBenchmark.kwargs_from_cli(parser.parse_args([]))
    stories = kwargs["stories"]
    self.assertEqual(len(stories), 10)

    # Ensure at least one story of type `idle` and one of type `media-playback`.
    # More importantly, ensure each one has the correct default.
    has_idle = False
    has_playback = False
    for story in stories:
      if isinstance(story, WebPowerIdleStory):
        has_idle = True
        self.assertEqual(story.idle_duration,
                         WebPowerIdleStory.DEFAULT_DURATION)
      elif isinstance(story, WebPowerMediaPlaybackStory):
        has_playback = True
        self.assertEqual(story.playback_duration,
                         WebPowerMediaPlaybackStory.DEFAULT_DURATION)
    self.assertTrue(has_idle)
    self.assertTrue(has_playback)

  def test_kwargs_from_cli_custom_duration_override(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerBenchmark.add_cli_arguments(parser)
    # Specifying an explicit --duration should override duration for all tests
    # that support this flag. (Pick a value that would avoid false positives.)
    expected_duration: Final[int] = 42
    self.assertNotEqual(expected_duration,
                        WebPowerIdleStory.DEFAULT_DURATION.total_seconds())
    self.assertNotEqual(
        expected_duration,
        WebPowerMediaPlaybackStory.DEFAULT_DURATION.total_seconds())
    args = parser.parse_args([f"--duration={expected_duration}s"])
    kwargs = WebPowerBenchmark.kwargs_from_cli(args)

    self.assertEqual(len(kwargs["stories"]), 10)
    for story in kwargs["stories"]:
      if isinstance(story, WebPowerIdleStory):
        self.assertEqual(story.idle_duration,
                         dt.timedelta(seconds=expected_duration))
      elif isinstance(story, WebPowerMediaPlaybackStory):
        self.assertEqual(story.playback_duration,
                         dt.timedelta(seconds=expected_duration))

  def test_kwargs_from_cli_custom_scenario_arguments(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerBenchmark.add_cli_arguments(parser)
    args = parser.parse_args([
        "--stories=idle-msn,scroll-cnn,page-load-cnn,media-playback-youtube",
        "--duration=45s",
        "--stabilization-time=5s",
        "--scrolls=12",
        "--input-rate=120",
        "--lead-wait-time=6s",
        "--page-loads=15",
        "--interval=4s",
        "--cool-off-time=20s",
        "--stats",
        "--volume=off",
    ])
    kwargs = WebPowerBenchmark.kwargs_from_cli(args)

    stories = kwargs["stories"]
    self.assertEqual(len(stories), 4)

    # 1. WebPowerIdleStory
    self.assertEqual(stories[0].name, "web-power-idle-msn")
    self.assertTrue(isinstance(stories[0], WebPowerIdleStory))
    self.assertEqual(stories[0].idle_duration, dt.timedelta(seconds=45))
    self.assertEqual(stories[0].stabilization_time, dt.timedelta(seconds=5))

    # 2. WebPowerScrollStory
    self.assertEqual(stories[1].name, "web-power-scroll-cnn")
    self.assertTrue(isinstance(stories[1], WebPowerScrollStory))
    self.assertEqual(stories[1].scroll_count, 12)
    self.assertEqual(stories[1].input_rate, 120)
    self.assertEqual(stories[1].lead_wait_time, dt.timedelta(seconds=6))

    # 3. WebPowerPageLoadStory
    self.assertEqual(stories[2].name, "web-power-page-load-cnn")
    self.assertTrue(isinstance(stories[2], WebPowerPageLoadStory))
    self.assertEqual(stories[2].page_load_count, 15)
    self.assertEqual(stories[2].interval, dt.timedelta(seconds=4))
    self.assertEqual(stories[2].lead_wait_time, dt.timedelta(seconds=6))
    self.assertEqual(stories[2].cool_off_time, dt.timedelta(seconds=20))

    # 4. WebPowerMediaPlaybackStory
    self.assertEqual(stories[3].name, "web-power-media-playback-youtube")
    self.assertTrue(isinstance(stories[3], WebPowerMediaPlaybackStory))
    self.assertEqual(stories[3].playback_duration, dt.timedelta(seconds=45))
    self.assertEqual(stories[3].stabilization_time, dt.timedelta(seconds=5))
    self.assertTrue(stories[3].stats)
    self.assertEqual(stories[3].volume, VolumeMode.OFF)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
