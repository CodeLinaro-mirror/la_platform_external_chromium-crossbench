# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any, ClassVar

from typing_extensions import override

from crossbench.benchmarks.power.base import PowerBenchmarkBase, PowerStory, \
    _value_or
from crossbench.parse import DurationParser

if TYPE_CHECKING:
  import argparse

  from crossbench.cli.parser import CBArgumentParser
  from crossbench.runner.run import Run


class PowerIdleStory(PowerStory):
  DEFAULT_DURATION: ClassVar[dt.timedelta] = dt.timedelta(seconds=80)
  DEFAULT_STABILIZATION_TIME: ClassVar[dt.timedelta] = dt.timedelta(seconds=10)

  @property
  @override
  def story_name(self) -> str:
    return "idle"

  def __init__(self,
               name_suffix: str,
               url: str,
               idle_duration: dt.timedelta | None = None,
               stabilization_time: dt.timedelta | None = None) -> None:
    self.stabilization_time = _value_or(stabilization_time,
                                        self.DEFAULT_STABILIZATION_TIME)
    idle_duration = _value_or(idle_duration, self.DEFAULT_DURATION)

    if idle_duration.total_seconds() == 0:
      # Indefinite idling. (Mapped to 1 year to avoid overflow.)
      idle_duration = dt.timedelta(days=365)
      total_duration = dt.timedelta(days=365)
    else:
      total_duration = (
          idle_duration + self.stabilization_time +
          PowerStory.DEFAULT_GRACE_PERIOD)

    self._idle_duration = idle_duration
    super().__init__(name_suffix, url, total_duration)

  @override
  def run(self, run: Run) -> None:
    with run.actions("Show URL", verbose=True) as actions:
      actions.show_url(self.url)

    with run.actions("Stabilization", verbose=True) as actions:
      actions.wait(self.stabilization_time)

    with run.actions("Idle", verbose=True) as actions:
      actions.wait(self._idle_duration)


class PowerIdleBenchmark(PowerBenchmarkBase):
  """Benchmark runner for Power Idle scenario."""

  NAME: ClassVar = f"{PowerBenchmarkBase.NAME}-idle"
  DEFAULT_STORY_CLS: ClassVar = PowerIdleStory

  @classmethod
  @override
  def add_cli_arguments(cls, parser: CBArgumentParser) -> CBArgumentParser:
    parser = super().add_cli_arguments(parser)
    default_s = cls.DEFAULT_STORY_CLS.DEFAULT_DURATION.total_seconds()
    parser.add_argument(
        "--duration",
        "--idle-duration",
        "--run-for",
        "--stop-after",
        dest="idle_duration",
        type=DurationParser.positive_or_zero_duration,
        default=cls.DEFAULT_STORY_CLS.DEFAULT_DURATION,
        help="How long to run the idle phase for. (0 indicates forever.) "
        f"(Default: {default_s:.0f}s)")
    return parser

  @classmethod
  @override
  def kwargs_from_cli(cls, args: argparse.Namespace) -> dict[str, Any]:
    kwargs = super().kwargs_from_cli(args)
    kwargs["idle_duration"] = args.idle_duration
    return kwargs
