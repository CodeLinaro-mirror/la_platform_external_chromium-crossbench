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
from crossbench.benchmarks.web_power.media_playback import AmbientMode, \
    WebPowerMediaPlaybackStory
from crossbench.benchmarks.web_power.page_load import WebPowerPageLoadStory
from crossbench.benchmarks.web_power.scroll import WebPowerScrollStory
from crossbench.benchmarks.web_power.volume_helper import VolumeMode
from crossbench.browsers.attributes import BrowserAttributes
from crossbench.cli.parser import CBArgumentParser
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.benchmarks.web_power.test_base import \
    BaseWebPowerBenchmarkTestCase


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

  def test_stories_from_names_non_canonical(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerBenchmark.add_cli_arguments(parser)
    args = parser.parse_args(["--stories=idle-yahoo"])
    story_filter = WebPowerConsolidatedStoryFilter.from_cli_args(
        WebPowerBenchmark.DEFAULT_STORY_CLS, args)
    stories = story_filter.stories

    self.assertEqual(len(stories), 1)
    self.assertEqual(stories[0].name, "web-power-idle-yahoo")
    self.assertEqual(stories[0].url, "https://www.yahoo.com")

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


class WebPowerBenchmarkTestCase(BaseWebPowerBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self) -> type[WebPowerBenchmark]:
    return WebPowerBenchmark

  def test_kwargs_from_cli_defaults_instantiates_all_types(self) -> None:
    args = self.parse_args()
    kwargs = WebPowerBenchmark.kwargs_from_cli(args)
    stories = kwargs["stories"]
    self.assertEqual(len(stories), 10)

    counts = {
        WebPowerIdleStory: 0,
        WebPowerScrollStory: 0,
        WebPowerPageLoadStory: 0,
        WebPowerMediaPlaybackStory: 0,
    }
    for story in stories:
      story_type = type(story)
      counts[story_type] += 1

    self.assertEqual(counts[WebPowerIdleStory], 3)
    self.assertEqual(counts[WebPowerScrollStory], 3)
    self.assertEqual(counts[WebPowerPageLoadStory], 3)
    self.assertEqual(counts[WebPowerMediaPlaybackStory], 1)

  def test_kwargs_from_cli_defaults_idle(self) -> None:
    kwargs = WebPowerBenchmark.kwargs_from_cli(self.parse_args())
    # We do not assert that a WebPowerIdleStory was found here;
    # test_kwargs_from_cli_defaults_instantiates_all_types ensures
    # we have at least one.
    for story in kwargs["stories"]:
      if not isinstance(story, WebPowerIdleStory):
        continue
      self.assertEqual(story.idle_duration, WebPowerIdleStory.DEFAULT_DURATION)
      self.assertEqual(story.stabilization_time,
                       story.site_config.default_stabilization_time)

  def test_kwargs_from_cli_defaults_scroll(self) -> None:
    kwargs = WebPowerBenchmark.kwargs_from_cli(self.parse_args())
    # test_kwargs_from_cli_defaults_instantiates_all_types ensures
    # we have at least one.
    for story in kwargs["stories"]:
      if not isinstance(story, WebPowerScrollStory):
        continue
      self.assertEqual(story.scroll_count,
                       WebPowerScrollStory.DEFAULT_SCROLL_COUNT)
      self.assertEqual(story.input_rate, WebPowerScrollStory.DEFAULT_INPUT_RATE)
      self.assertEqual(story.stabilization_time,
                       story.site_config.default_stabilization_time)

  def test_kwargs_from_cli_defaults_page_load(self) -> None:
    kwargs = WebPowerBenchmark.kwargs_from_cli(self.parse_args())
    # test_kwargs_from_cli_defaults_instantiates_all_types ensures
    # we have at least one.
    for story in kwargs["stories"]:
      if not isinstance(story, WebPowerPageLoadStory):
        continue
      expected_count = (
          WebPowerPageLoadStory.DEFAULT_CNN_PAGE_LOAD_COUNT
          if story.name.endswith("cnn") else
          WebPowerPageLoadStory.DEFAULT_PAGE_LOAD_COUNT)
      self.assertEqual(story.page_load_count, expected_count)
      self.assertEqual(story.interval, WebPowerPageLoadStory.DEFAULT_INTERVAL)
      self.assertEqual(story.stabilization_time,
                       story.site_config.default_stabilization_time)

  def test_kwargs_from_cli_defaults_media_playback(self) -> None:
    kwargs = WebPowerBenchmark.kwargs_from_cli(self.parse_args())
    # test_kwargs_from_cli_defaults_instantiates_all_types ensures
    # we have at least one.
    for story in kwargs["stories"]:
      if not isinstance(story, WebPowerMediaPlaybackStory):
        continue
      self.assertEqual(story.playback_duration,
                       WebPowerMediaPlaybackStory.DEFAULT_DURATION)
      self.assertEqual(story.stabilization_time,
                       story.site_config.default_stabilization_time)
      self.assertEqual(story.stats, WebPowerMediaPlaybackStory.DEFAULT_STATS)
      self.assertEqual(story.volume, WebPowerMediaPlaybackStory.DEFAULT_VOLUME)
      self.assertEqual(story.ambient_mode,
                       WebPowerMediaPlaybackStory.DEFAULT_AMBIENT_MODE)

  def test_kwargs_from_cli_custom_duration_override(self) -> None:
    # Specifying an explicit --duration should override duration for all tests
    # that support this flag. (Pick a value that would avoid false positives.)
    expected_duration: Final[int] = 42
    self.assertNotEqual(expected_duration,
                        WebPowerIdleStory.DEFAULT_DURATION.total_seconds())
    self.assertNotEqual(
        expected_duration,
        WebPowerMediaPlaybackStory.DEFAULT_DURATION.total_seconds())
    args = self.parse_args(f"--duration={expected_duration}s")
    kwargs = WebPowerBenchmark.kwargs_from_cli(args)

    self.assertEqual(len(kwargs["stories"]), 10)
    for story in kwargs["stories"]:
      match story:
        case WebPowerIdleStory():
          self.assertEqual(story.idle_duration,
                           dt.timedelta(seconds=expected_duration))
        case WebPowerMediaPlaybackStory():
          self.assertEqual(story.playback_duration,
                           dt.timedelta(seconds=expected_duration))

  def test_kwargs_from_cli_custom_scenario_arguments(self) -> None:
    args = self.parse_args(
        "--stories=idle-msn,scroll-cnn,page-load-cnn,media-playback-youtube",
        "--duration=45s",
        "--stabilization-time=5s",
        "--scrolls=12",
        "--input-rate=120",
        "--page-loads=15",
        "--interval=4s",
        "--stats",
        "--volume=off",
        "--ambient-mode=unchanged",
    )
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
    self.assertEqual(stories[1].stabilization_time, dt.timedelta(seconds=5))

    # 3. WebPowerPageLoadStory
    self.assertEqual(stories[2].name, "web-power-page-load-cnn")
    self.assertTrue(isinstance(stories[2], WebPowerPageLoadStory))
    self.assertEqual(stories[2].page_load_count, 15)
    self.assertEqual(stories[2].interval, dt.timedelta(seconds=4))
    self.assertEqual(stories[2].stabilization_time, dt.timedelta(seconds=5))

    # 4. WebPowerMediaPlaybackStory
    self.assertEqual(stories[3].name, "web-power-media-playback-youtube")
    self.assertTrue(isinstance(stories[3], WebPowerMediaPlaybackStory))
    self.assertEqual(stories[3].playback_duration, dt.timedelta(seconds=45))
    self.assertEqual(stories[3].stabilization_time, dt.timedelta(seconds=5))
    self.assertTrue(stories[3].stats)
    self.assertEqual(stories[3].volume, VolumeMode.OFF)
    self.assertEqual(stories[3].ambient_mode, AmbientMode.UNCHANGED)

  def test_extra_flags_story_autoplay_assignment(self) -> None:
    args = self.parse_args(
        "--stories=idle-msn,page-load-cnn,media-playback-youtube",)
    kwargs = WebPowerBenchmark.kwargs_from_cli(args)
    benchmark = WebPowerBenchmark(**kwargs)

    for story in benchmark.stories:
      flags = benchmark.extra_flags(BrowserAttributes.CHROMIUM_BASED, story)
      is_playback = isinstance(story, WebPowerMediaPlaybackStory)
      self.assertEqual("--autoplay-policy" in flags, is_playback)
      if is_playback:
        self.assertEqual(flags["--autoplay-policy"], "no-user-gesture-required")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
