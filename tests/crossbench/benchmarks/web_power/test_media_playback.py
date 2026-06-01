# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt

from typing_extensions import override

from crossbench.benchmarks.web_power.media_playback import \
    WebPowerMediaPlaybackBenchmark, WebPowerMediaPlaybackStory
from crossbench.cli.parser import CBArgumentParser
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.benchmarks.helper import BaseBenchmarkTestCase


class WebPowerMediaPlaybackStoryTestCase(BaseCrossbenchTestCase):

  def test_instantiate_default(self) -> None:
    story = WebPowerMediaPlaybackStory(
        name_suffix="test",
        url="https://youtube.com",
    )
    self.assertEqual(story.url, "https://youtube.com")
    self.assertEqual(story.playback_duration, story.DEFAULT_DURATION)
    self.assertEqual(story.stabilization_time, story.DEFAULT_STABILIZATION_TIME)
    self.assertEqual(story.stats, story.DEFAULT_STATS)
    self.assertEqual(story.volume, story.DEFAULT_VOLUME)

  def test_instantiate_custom(self) -> None:
    duration = dt.timedelta(seconds=30)
    stabilization = dt.timedelta(seconds=5)
    story = WebPowerMediaPlaybackStory(
        name_suffix="test",
        url="https://youtube.com",
        playback_duration=duration,
        stabilization_time=stabilization,
        stats=True,
        volume="off",
    )
    self.assertEqual(story.url, "https://youtube.com")
    self.assertEqual(story.playback_duration, duration)
    self.assertEqual(story.stabilization_time, stabilization)
    self.assertTrue(story.stats)
    self.assertEqual(story.volume, "off")


class WebPowerMediaPlaybackBenchmarkTestCase(BaseBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self) -> type[WebPowerMediaPlaybackBenchmark]:
    return WebPowerMediaPlaybackBenchmark

  def test_kwargs_from_cli_defaults(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerMediaPlaybackBenchmark.add_cli_arguments(parser)
    args = parser.parse_args(["--site", "youtube"])
    kwargs = WebPowerMediaPlaybackBenchmark.kwargs_from_cli(args)
    self.assertEqual(kwargs["site_key"], "youtube")
    self.assertEqual(kwargs["volume"], "on")
    self.assertEqual(kwargs["playback_duration"],
                     WebPowerMediaPlaybackStory.DEFAULT_DURATION)
    self.assertEqual(kwargs["stabilization_time"],
                     WebPowerMediaPlaybackStory.DEFAULT_STABILIZATION_TIME)
    self.assertFalse(kwargs["stats"])

  def test_kwargs_from_cli_custom(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerMediaPlaybackBenchmark.add_cli_arguments(parser)
    args = parser.parse_args([
        "--site=youtube",
        "--volume=off",
        "--playback-duration=45s",
        "--stabilization-time=15s",
        "--stats",
    ])
    kwargs = WebPowerMediaPlaybackBenchmark.kwargs_from_cli(args)
    self.assertEqual(kwargs["site_key"], "youtube")
    self.assertEqual(kwargs["volume"], "off")
    self.assertEqual(kwargs["playback_duration"], dt.timedelta(seconds=45))
    self.assertEqual(kwargs["stabilization_time"], dt.timedelta(seconds=15))
    self.assertTrue(kwargs["stats"])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
