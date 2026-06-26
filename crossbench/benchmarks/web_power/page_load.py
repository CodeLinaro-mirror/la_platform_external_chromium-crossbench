# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import logging
from typing import TYPE_CHECKING, ClassVar

from typing_extensions import override

from crossbench.action_runner.action.clear_cache import ClearCacheAction
from crossbench.action_runner.action.enums import WindowTarget
from crossbench.benchmarks.loading.playback_controller import \
    PeriodicPlaybackController
from crossbench.benchmarks.web_power.base import WebPowerBenchmarkBase, \
    WebPowerSiteConfig, WebPowerStory, WebPowerStoryFilter, _value_or
from crossbench.parse import DurationParser, NumberParser

if TYPE_CHECKING:
  from crossbench.cli.parser import CBArgumentParser
  from crossbench.runner.run import Run


class WebPowerPageLoadStory(WebPowerStory):
  IS_SCENARIO_CLASS = True
  DEFAULT_PAGE_LOAD_COUNT: ClassVar[int] = 40
  # TODO: Test all other sites with 10 page loads and converge on a single
  # default value once it's proven that the variance is low.
  DEFAULT_CNN_PAGE_LOAD_COUNT: ClassVar[int] = 10
  DEFAULT_INTERVAL: ClassVar[dt.timedelta] = dt.timedelta(seconds=3)
  DEFAULT_LEAD_WAIT_TIME: ClassVar[dt.timedelta] = dt.timedelta(seconds=10)
  DEFAULT_COOL_OFF_TIME: ClassVar[dt.timedelta] = dt.timedelta(seconds=60)

  @classmethod
  @override
  def story_name_cls(cls) -> str:
    return "page-load"

  def __init__(self,
               name_suffix: str,
               site_config: WebPowerSiteConfig,
               page_load_count: int | None = None,
               interval: dt.timedelta | None = None,
               lead_wait_time: dt.timedelta | None = None,
               cool_off_time: dt.timedelta | None = None) -> None:
    default_count = (
        self.DEFAULT_CNN_PAGE_LOAD_COUNT
        if name_suffix == "cnn" else self.DEFAULT_PAGE_LOAD_COUNT)
    self.page_load_count = _value_or(page_load_count, default_count)
    self.interval = _value_or(interval, self.DEFAULT_INTERVAL)
    self.lead_wait_time = _value_or(lead_wait_time, self.DEFAULT_LEAD_WAIT_TIME)
    self.cool_off_time = _value_or(cool_off_time, self.DEFAULT_COOL_OFF_TIME)

    total_duration = (
        self.lead_wait_time + self.cool_off_time +
        self.page_load_count * self.interval +
        WebPowerStory.DEFAULT_GRACE_PERIOD)
    super().__init__(name_suffix, site_config, total_duration)

  @override
  def setup(self, run: Run) -> None:
    logging.info("Initial lead wait time: %s", self.lead_wait_time)
    with run.actions("Lead_Wait", verbose=True) as actions:
      actions.wait(self.lead_wait_time)

    # The initial setup load in a new tab guarantees that the page-load loop
    # (which starts by closing tab_index=0) always has a tab to close.
    logging.info("Initial setup page load (new tab).")
    with run.actions("Initial_Setup_Load", verbose=True) as actions:
      actions.show_url(self.url, target=WindowTarget.NEW_TAB)
      if self.cool_off_time.total_seconds() > 0:
        actions.wait(self.cool_off_time)

  @override
  def run(self, run: Run) -> None:
    logging.info("Starting page-load loop.")
    playback = PeriodicPlaybackController(self.page_load_count, self.interval)
    with run.actions(
        "Run", verbose=True, performance_mark=WebPowerStory.MEASUREMENT_MARK):
      for i in playback:
        # Clearing the cache from inside of the power-measured window is the
        # lesser evil given current technical difficulties with:
        #  1. Currently available cache-clearing mechanisms.
        #  2. The resolution of power-measuring instruments such as ODPM.
        with run.actions(f"Cache_Clear_{i}"):
          run.action_runner.clear_cache(ClearCacheAction())
        with run.actions(f"Close_Tab_{i}"):
          run.browser.close_tab(tab_index=0, timeout=dt.timedelta(seconds=1))
        with run.actions(f"Page_Load_{i}") as actions:
          actions.show_url(self.url, target=WindowTarget.NEW_TAB)


class WebPowerPageLoadStoryFilter(WebPowerStoryFilter[WebPowerPageLoadStory]):
  """Story filter for Web Power page-load stories."""

  IS_SCENARIO_CLASS = True
  STORY_CLS = WebPowerPageLoadStory


class WebPowerPageLoadBenchmark(WebPowerBenchmarkBase):
  """Benchmark runner for Power Page-Load scenario."""

  IS_SCENARIO_CLASS = True
  NAME: ClassVar = f"{WebPowerBenchmarkBase.NAME}-page-load"
  DEFAULT_STORY_CLS: ClassVar = WebPowerPageLoadStory
  STORY_FILTER_CLS: ClassVar = WebPowerPageLoadStoryFilter

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
    default_interval_s = story_cls.DEFAULT_INTERVAL.total_seconds()
    default_cool_s = story_cls.DEFAULT_COOL_OFF_TIME.total_seconds()
    # TODO(eladalon): Avoid accessing private option_string_actions.
    actions = parser._option_string_actions  # noqa: SLF001
    if "--lead-wait-time" not in actions:
      parser.add_argument(
          "--lead-wait-time",
          "--wait",
          dest="lead_wait_time",
          type=DurationParser.positive_or_zero_duration,
          help=("Initial wait time after starting browser to "
                "recover from launching."),
      )
    parser.add_argument(
        "--page-loads",
        "--page-load-count",
        dest="page_load_count",
        type=NumberParser.positive_int,
        default=None,
        help="Number of times to reload the page. "
        f"(Default: {story_cls.DEFAULT_PAGE_LOAD_COUNT}, "
        f"CNN default: {story_cls.DEFAULT_CNN_PAGE_LOAD_COUNT})")
    parser.add_argument(
        "--interval",
        type=DurationParser.positive_duration,
        default=story_cls.DEFAULT_INTERVAL,
        help="Wait time between page loads. "
        f"(Default: {default_interval_s:.0f}s)")
    parser.add_argument(
        "--cool-off-time",
        "--cool-off",
        dest="cool_off_time",
        type=DurationParser.positive_or_zero_duration,
        default=story_cls.DEFAULT_COOL_OFF_TIME,
        help="Initial cooling-off period before measurement. "
        "This is a workaround for the fact that service workers on some sites "
        "do a lot of work during first iterations, and calm down later. "
        # Ideally, we should be able to clear the service worker between
        # iterations and measure this work too. But for now, it's better to
        # consistently not measure it, then to inconsistently measure it.
        f"(Default: {default_cool_s:.0f}s)")
    return parser
