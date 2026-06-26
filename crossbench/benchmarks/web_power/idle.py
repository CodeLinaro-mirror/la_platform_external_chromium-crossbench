# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any, ClassVar

from typing_extensions import override

from crossbench.benchmarks.web_power.base import WebPowerBenchmarkBase, \
    WebPowerSiteConfig, WebPowerStory, WebPowerStoryFilter, _value_or
from crossbench.parse import DurationParser

if TYPE_CHECKING:
  import argparse

  from crossbench.cli.parser import CBArgumentParser
  from crossbench.runner.run import Run


class WebPowerIdleStory(WebPowerStory):
  DEFAULT_DURATION: ClassVar[dt.timedelta] = dt.timedelta(seconds=80)
  DEFAULT_STABILIZATION_TIME: ClassVar[dt.timedelta] = dt.timedelta(seconds=10)

  @classmethod
  @override
  def story_name_cls(cls) -> str:
    return "idle"

  def __init__(self,
               name_suffix: str,
               site_config: WebPowerSiteConfig,
               duration: dt.timedelta | None = None,
               stabilization_time: dt.timedelta | None = None) -> None:
    self.stabilization_time = _value_or(stabilization_time,
                                        self.DEFAULT_STABILIZATION_TIME)
    duration = _value_or(duration, self.DEFAULT_DURATION)

    if duration.total_seconds() == 0:
      # Indefinite idling. (Mapped to 1 year to avoid overflow.)
      duration = dt.timedelta(days=365)
      total_duration = dt.timedelta(days=365)
    else:
      total_duration = (
          duration + self.stabilization_time +
          WebPowerStory.DEFAULT_GRACE_PERIOD)

    self._idle_duration = duration
    super().__init__(name_suffix, site_config, total_duration)

  @property
  def idle_duration(self) -> dt.timedelta:
    return self._idle_duration

  @override
  def setup(self, run: Run) -> None:
    with run.actions("Show URL", verbose=True) as actions:
      actions.show_url(self.url)

    with run.actions("Stabilization", verbose=True) as actions:
      actions.wait(self.stabilization_time)

  @override
  def run(self, run: Run) -> None:
    with run.actions(
        "Idle", verbose=True,
        performance_mark=WebPowerStory.MEASUREMENT_MARK) as actions:
      actions.wait(self._idle_duration)


class WebPowerIdleStoryFilter(WebPowerStoryFilter[WebPowerIdleStory]):
  """Story filter for Web Power idle stories."""

  STORY_CLS = WebPowerIdleStory

  @classmethod
  @override
  def kwargs_from_cli(cls, args: argparse.Namespace) -> dict[str, Any]:
    kwargs = super().kwargs_from_cli(args)
    kwargs["story_kwargs"] = {
        "duration": args.duration,
        "stabilization_time": args.stabilization_time,
    }
    return kwargs


class WebPowerIdleBenchmark(WebPowerBenchmarkBase):
  """Benchmark runner for Power Idle scenario."""

  NAME: ClassVar = f"{WebPowerBenchmarkBase.NAME}-idle"
  DEFAULT_STORY_CLS: ClassVar = WebPowerIdleStory
  STORY_FILTER_CLS: ClassVar = WebPowerIdleStoryFilter

  @classmethod
  @override
  def add_cli_arguments(cls, parser: CBArgumentParser) -> CBArgumentParser:
    parser = super().add_cli_arguments(parser)
    default_s = cls.DEFAULT_STORY_CLS.DEFAULT_DURATION.total_seconds()
    parser.add_argument(
        "--duration",
        type=DurationParser.positive_or_zero_duration,
        default=cls.DEFAULT_STORY_CLS.DEFAULT_DURATION,
        help="How long to run the idle phase for. (0 indicates forever.) "
        f"(Default: {default_s:.0f}s)")
    default_stabilization_s = (
        cls.DEFAULT_STORY_CLS.DEFAULT_STABILIZATION_TIME.total_seconds())
    parser.add_argument(
        "--stabilization",
        "--stabilization-time",
        dest="stabilization_time",
        type=DurationParser.positive_or_zero_duration,
        default=cls.DEFAULT_STORY_CLS.DEFAULT_STABILIZATION_TIME,
        help="How long to wait after setting up the page to stabilize. "
        f"(Default: {default_stabilization_s:.0f}s)",
    )
    return parser
