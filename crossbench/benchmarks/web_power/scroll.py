# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import atexit
import datetime as dt
import tempfile
from typing import TYPE_CHECKING, ClassVar

from typing_extensions import override

from crossbench import path as pth
from crossbench.benchmarks.web_power.base import WebPowerBenchmarkBase, \
    WebPowerSiteConfig, WebPowerStory, WebPowerStoryFilter, _value_or
from crossbench.benchmarks.web_power.scroll_gen import GeneratorConfig, \
    generate_scroll_commands
from crossbench.parse import DurationParser, NumberParser

if TYPE_CHECKING:
  from crossbench.cli.parser import CBArgumentParser
  from crossbench.runner.run import Run


class WebPowerScrollStory(WebPowerStory):
  IS_SCENARIO_CLASS = True
  DEFAULT_SCROLL_COUNT: ClassVar[int] = 5
  DEFAULT_INPUT_RATE: ClassVar[int] = 240
  # Enforce a minimum time before scrolling. Otherwise the page does not
  # fully load, the down/up scrolls do not end up in the same place, and
  # subsequent repetitions might accidentally trigger pull-to-refresh.
  MIN_LEAD_WAIT_TIME: ClassVar[dt.timedelta] = dt.timedelta(seconds=3)
  DEFAULT_LEAD_WAIT_TIME: ClassVar[dt.timedelta] = dt.timedelta(seconds=10)

  @classmethod
  @override
  def story_name_cls(cls) -> str:
    return "scroll"

  @property
  def scroll_count(self) -> int:
    return self.config.scroll_count

  @property
  def input_rate(self) -> int:
    return self.config.input_rate

  def __init__(self,
               name_suffix: str,
               site_config: WebPowerSiteConfig,
               scroll_count: int | None = None,
               input_rate: int | None = None,
               lead_wait_time: dt.timedelta | None = None) -> None:
    # TODO(eladalon): Eliminate duplication with page_load.py by moving
    # lead_wait_time into PowerStory base class.
    self.lead_wait_time = _value_or(lead_wait_time, self.DEFAULT_LEAD_WAIT_TIME)
    if self.lead_wait_time < self.MIN_LEAD_WAIT_TIME:
      min_s = self.MIN_LEAD_WAIT_TIME.total_seconds()
      req_s = self.lead_wait_time.total_seconds()
      raise ValueError(
          "The web-power-scroll benchmark requires a minimum lead-wait "
          f"time of {min_s:.0f}s. (Requested {req_s:.1f}s.) This ensures "
          "the page fully loads, the up/down scroll positions balance out, "
          "and subsequent repetitions do not trigger pull-to-refresh.")

    self.config = GeneratorConfig(
        input_rate=_value_or(input_rate, self.DEFAULT_INPUT_RATE),
        scroll_count=_value_or(scroll_count, self.DEFAULT_SCROLL_COUNT))

    total_duration = (
        self.lead_wait_time + self.config.sequence_duration() +
        WebPowerStory.DEFAULT_GRACE_PERIOD)
    super().__init__(name_suffix, site_config, total_duration)

    self.local_file: pth.LocalPath | None = None
    self.remote_file: pth.AnyPath | None = None

  @override
  def setup(self, run: Run) -> None:
    assert (self.local_file is None)
    assert (self.remote_file is None)

    if not run.browser_platform.is_android:
      raise RuntimeError(
          "The web-power-scroll benchmark is only supported on Android.")

    # Register cleanup at exit, in case an exception is raised in between
    # setup() and run() being called.
    atexit.register(self.clear_files, run)

    try:
      with run.actions("Generate_Scrolls", verbose=True) as actions:
        display_res = run.browser_platform.display_resolution()
        evemu_data = generate_scroll_commands(self.config, display_res)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".evemu", delete=False) as f:
          f.write(evemu_data)
          self.local_file = pth.LocalPath(f.name)

      with run.actions("Push_Scrolls", verbose=True) as actions:
        self.remote_file = run.browser_platform.path(
            "/data/local/tmp/scrolling_sequence.evemu")
        run.browser_platform.push(self.local_file, self.remote_file)

      with run.actions("Lead_Wait", verbose=True) as actions:
        actions.show_url(self.url)
        actions.wait(self.lead_wait_time)

    except Exception:
      self.clear_files(run)
      raise

  @override
  def run(self, run: Run) -> None:
    assert (self.local_file is not None)
    assert (self.remote_file is not None)

    try:
      with run.actions(
          "Run", verbose=True, performance_mark=WebPowerStory.MEASUREMENT_MARK):
        with run.actions("Scroll"):
          run.browser_platform.sh("uinput", f"{self.remote_file}")

    finally:
      self.clear_files(run)

  def clear_files(self, run: Run) -> None:
    atexit.unregister(self.clear_files)
    if self.local_file is not None:
      self.local_file.unlink(missing_ok=True)
      self.local_file = None
    if self.remote_file is not None:
      run.browser_platform.rm(self.remote_file, missing_ok=True)
      self.remote_file = None


class WebPowerScrollStoryFilter(WebPowerStoryFilter[WebPowerScrollStory]):
  """Story filter for Web Power scroll stories."""

  IS_SCENARIO_CLASS = True
  STORY_CLS = WebPowerScrollStory


class WebPowerScrollBenchmark(WebPowerBenchmarkBase):
  """Benchmark runner for Power Scroll scenario using legacy EVEMU emulation."""

  IS_SCENARIO_CLASS = True
  NAME: ClassVar = f"{WebPowerBenchmarkBase.NAME}-scroll"
  DEFAULT_STORY_CLS: ClassVar = WebPowerScrollStory
  STORY_FILTER_CLS: ClassVar = WebPowerScrollStoryFilter

  @classmethod
  def _scroll_lead_wait_time(cls, value: str) -> dt.timedelta:
    duration = DurationParser.positive_or_zero_duration(value)
    if duration < WebPowerScrollStory.MIN_LEAD_WAIT_TIME:
      min_s = WebPowerScrollStory.MIN_LEAD_WAIT_TIME.total_seconds()
      raise argparse.ArgumentTypeError(
          "The web-power-scroll benchmark requires a minimum lead-wait "
          f"time of {min_s:.0f}s. (Requested {duration.total_seconds():.1f}s.)")
    return duration

  @classmethod
  @override
  def add_cli_arguments(cls, parser: CBArgumentParser) -> CBArgumentParser:
    parser = super().add_cli_arguments(parser)
    story_cls = cls.DEFAULT_STORY_CLS
    parser.set_defaults(lead_wait_time=story_cls.DEFAULT_LEAD_WAIT_TIME)
    return parser

  @classmethod
  @override
  def add_scenario_cli_arguments(cls,
                                 parser: CBArgumentParser) -> CBArgumentParser:
    story_cls = cls.DEFAULT_STORY_CLS
    # TODO(eladalon): Avoid accessing private option_string_actions.
    actions = parser._option_string_actions  # noqa: SLF001
    if "--lead-wait-time" not in actions:
      parser.add_argument(
          "--lead-wait-time",
          "--wait",
          dest="lead_wait_time",
          type=cls._scroll_lead_wait_time,
          help=("Initial wait time after starting browser to "
                "recover from launching."),
      )
    parser.add_argument(
        "--scrolls",
        "--scroll-count",
        dest="scroll_count",
        type=NumberParser.positive_int,
        default=None,
        help="Number of times to repeat the up/down scroll sequence "
        f"(Default: {story_cls.DEFAULT_SCROLL_COUNT})")
    parser.add_argument(
        "--input-rate",
        "--rate",
        dest="input_rate",
        type=NumberParser.positive_int,
        default=None,
        help="Frequency of synthetic scroll touch events in Hz. "
        f"(Default: {story_cls.DEFAULT_INPUT_RATE}Hz)")
    return parser
