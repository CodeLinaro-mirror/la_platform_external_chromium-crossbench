# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt

from typing_extensions import override

from crossbench.benchmarks.web_power.idle import WebPowerIdleBenchmark, \
    WebPowerIdleStory
from crossbench.cli.parser import CBArgumentParser
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.benchmarks.helper import BaseBenchmarkTestCase


class WebPowerIdleStoryTestCase(BaseCrossbenchTestCase):

  def test_instantiate_default(self) -> None:
    story = WebPowerIdleStory(
        name_suffix="test",
        url="https://www.cnn.com",
    )
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story._idle_duration, story.DEFAULT_DURATION)
    self.assertEqual(story.stabilization_time, story.DEFAULT_STABILIZATION_TIME)

  def test_instantiate_custom(self) -> None:
    duration = dt.timedelta(seconds=30)
    stabilization = dt.timedelta(seconds=5)
    story = WebPowerIdleStory(
        name_suffix="test",
        url="https://www.cnn.com",
        idle_duration=duration,
        stabilization_time=stabilization,
    )
    self.assertEqual(story.url, "https://www.cnn.com")
    self.assertEqual(story._idle_duration, duration)
    self.assertEqual(story.stabilization_time, stabilization)

  def test_instantiate_forever(self) -> None:
    story = WebPowerIdleStory(
        name_suffix="test",
        url="https://www.cnn.com",
        idle_duration=dt.timedelta(seconds=0),
    )
    # A duration of 0s represents infinite/indefinite idling, which is
    # mapped internally to a large value (at least a year) to avoid overflow.
    self.assertGreaterEqual(story._idle_duration, dt.timedelta(days=365))
    self.assertGreaterEqual(story.duration, dt.timedelta(days=365))


class WebPowerIdleBenchmarkTestCase(BaseBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self) -> type[WebPowerIdleBenchmark]:
    return WebPowerIdleBenchmark

  def test_kwargs_from_cli_defaults(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerIdleBenchmark.add_cli_arguments(parser)
    args = parser.parse_args(["--site", "cnn"])
    kwargs = WebPowerIdleBenchmark.kwargs_from_cli(args)
    self.assertEqual(kwargs["site_key"], "cnn")
    self.assertEqual(kwargs["idle_duration"],
                     WebPowerIdleStory.DEFAULT_DURATION)
    self.assertEqual(kwargs["stabilization_time"],
                     WebPowerIdleStory.DEFAULT_STABILIZATION_TIME)

  def test_kwargs_from_cli_custom(self) -> None:
    parser = CBArgumentParser()
    parser = WebPowerIdleBenchmark.add_cli_arguments(parser)
    args = parser.parse_args([
        "--site=cnn",
        "--idle-duration=45s",
        "--stabilization-time=15s",
    ])
    kwargs = WebPowerIdleBenchmark.kwargs_from_cli(args)
    self.assertEqual(kwargs["site_key"], "cnn")
    self.assertEqual(kwargs["idle_duration"], dt.timedelta(seconds=45))
    self.assertEqual(kwargs["stabilization_time"], dt.timedelta(seconds=15))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
