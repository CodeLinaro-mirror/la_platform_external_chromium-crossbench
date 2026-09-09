# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt

from typing_extensions import override

from crossbench.benchmarks.web_power.base import WebPowerSiteConfig
from crossbench.benchmarks.web_power.media_playback import AmbientMode, \
    WebPowerMediaPlaybackBenchmark, WebPowerMediaPlaybackStory
from crossbench.benchmarks.web_power.volume_helper import VolumeMode
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.benchmarks.web_power.test_base import \
    BaseWebPowerBenchmarkTestCase


class WebPowerMediaPlaybackStoryTestCase(BaseCrossbenchTestCase):

  def test_instantiate_default(self) -> None:
    story = WebPowerMediaPlaybackStory(
        name_suffix="test",
        site_config=WebPowerSiteConfig(url="https://youtube.com"),
    )
    self.assertEqual(story.url, "https://youtube.com")
    self.assertEqual(story.playback_duration, story.DEFAULT_DURATION)
    self.assertEqual(story.stabilization_time,
                     story.site_config.default_stabilization_time)
    self.assertEqual(story.stats, story.DEFAULT_STATS)
    self.assertEqual(story.volume, story.DEFAULT_VOLUME)
    self.assertEqual(story.ambient_mode, story.DEFAULT_AMBIENT_MODE)

  def test_instantiate_custom(self) -> None:
    duration = dt.timedelta(seconds=30)
    stabilization = dt.timedelta(seconds=5)
    story = WebPowerMediaPlaybackStory(
        name_suffix="test",
        site_config=WebPowerSiteConfig(url="https://youtube.com"),
        duration=duration,
        stabilization_time=stabilization,
        stats=True,
        volume=VolumeMode.OFF,
        ambient_mode=AmbientMode.UNCHANGED,
    )
    self.assertEqual(story.url, "https://youtube.com")
    self.assertEqual(story.playback_duration, duration)
    self.assertEqual(story.stabilization_time, stabilization)
    self.assertTrue(story.stats)
    self.assertEqual(story.volume, VolumeMode.OFF)
    self.assertEqual(story.ambient_mode, AmbientMode.UNCHANGED)


class WebPowerMediaPlaybackBenchmarkTestCase(BaseWebPowerBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self) -> type[WebPowerMediaPlaybackBenchmark]:
    return WebPowerMediaPlaybackBenchmark

  def test_kwargs_from_cli_defaults(self) -> None:
    args = self.parse_args("--site", "youtube")
    kwargs = WebPowerMediaPlaybackBenchmark.kwargs_from_cli(args)
    [story] = kwargs["stories"]
    self.assertEqual(story.url, "https://www.youtube.com/watch?v=XITHbsUUlYI")
    self.assertEqual(story.volume, "on")
    self.assertEqual(story.playback_duration,
                     WebPowerMediaPlaybackStory.DEFAULT_DURATION)
    self.assertEqual(story.stabilization_time,
                     story.site_config.default_stabilization_time)
    self.assertFalse(story.stats)
    self.assertEqual(story.ambient_mode, AmbientMode.OFF)

  def test_kwargs_from_cli_custom(self) -> None:
    args = self.parse_args(
        "--site=youtube",
        "--volume=off",
        "--duration=45s",
        "--stabilization-time=15s",
        "--stats",
        "--ambient-mode=unchanged",
    )
    kwargs = WebPowerMediaPlaybackBenchmark.kwargs_from_cli(args)
    [story] = kwargs["stories"]
    self.assertEqual(story.url, "https://www.youtube.com/watch?v=XITHbsUUlYI")
    self.assertEqual(story.volume, "off")
    self.assertEqual(story.playback_duration, dt.timedelta(seconds=45))
    self.assertEqual(story.stabilization_time, dt.timedelta(seconds=15))
    self.assertTrue(story.stats)
    self.assertEqual(story.ambient_mode, AmbientMode.UNCHANGED)

  def test_kwargs_from_cli_fullscreen(self) -> None:
    args = self.parse_args("--site=youtube", "--fullscreen")
    kwargs = WebPowerMediaPlaybackBenchmark.kwargs_from_cli(args)
    [story] = kwargs["stories"]
    self.assertTrue(story.fullscreen)

    args = self.parse_args("--site=youtube", "--no-fullscreen")
    kwargs = WebPowerMediaPlaybackBenchmark.kwargs_from_cli(args)
    [story] = kwargs["stories"]
    self.assertFalse(story.fullscreen)

  def test_kwargs_from_cli_ambient_mode(self) -> None:
    for mode_str, mode_enum in (
        ("on", AmbientMode.ON),
        ("off", AmbientMode.OFF),
        ("unchanged", AmbientMode.UNCHANGED),
    ):
      args = self.parse_args("--site=youtube", f"--ambient-mode={mode_str}")
      kwargs = WebPowerMediaPlaybackBenchmark.kwargs_from_cli(args)
      [story] = kwargs["stories"]
      self.assertEqual(story.ambient_mode, mode_enum)

  def test_kwargs_from_cli_volume(self) -> None:
    for vol, expected_vol in (
        ("off", VolumeMode.OFF),
        ("on", VolumeMode.ON),
        ("unchanged", VolumeMode.UNCHANGED),
    ):
      args = self.parse_args("--site=youtube", f"--volume={vol}")
      kwargs = WebPowerMediaPlaybackBenchmark.kwargs_from_cli(args)
      [story] = kwargs["stories"]
      self.assertEqual(story.volume, expected_vol)

  def test_kwargs_from_cli_invalid(self) -> None:
    with self.assertRaisesRegex(argparse.ArgumentError, "--ambient-mode"):
      self.parse_args("--ambient-mode=invalid")
    with self.assertRaisesRegex(argparse.ArgumentError, "--volume"):
      self.parse_args("--volume=invalid")
    with self.assertRaisesRegex(argparse.ArgumentError, "--duration"):
      self.parse_args("--duration=-1s")
    with self.assertRaisesRegex(argparse.ArgumentError, "--duration"):
      self.parse_args("--duration=0s")

  def test_from_cli_args(self) -> None:
    args = self.parse_args(
        "--site=youtube",
        "--stats",
        "--volume=off",
        "--ambient-mode=on",
        "--no-fullscreen",
        "--duration=30s",
    )
    benchmark = WebPowerMediaPlaybackBenchmark.from_cli_args(args)
    self.assertEqual(len(benchmark.stories), 1)
    story = benchmark.stories[0]
    self.assertIsInstance(story, WebPowerMediaPlaybackStory)
    self.assertTrue(story.stats)
    self.assertEqual(story.volume, VolumeMode.OFF)
    self.assertEqual(story.ambient_mode, AmbientMode.ON)
    self.assertFalse(story.fullscreen)
    self.assertEqual(story.playback_duration, dt.timedelta(seconds=30))



if __name__ == "__main__":
  test_helper.run_pytest(__file__)
