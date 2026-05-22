# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import tempfile
from typing import TYPE_CHECKING, Any, ClassVar

from typing_extensions import override

from crossbench import path as pth
from crossbench.benchmarks.web_power.base import WebPowerBenchmarkBase, \
    WebPowerStory, _value_or
from crossbench.benchmarks.web_power.scroll_gen import GeneratorConfig, \
    generate_scroll_commands
from crossbench.parse import DurationParser

if TYPE_CHECKING:
  import argparse

  from crossbench.cli.parser import CBArgumentParser
  from crossbench.runner.run import Run


class WebPowerScrollStory(WebPowerStory):
  DEFAULT_SCROLL_COUNT: ClassVar[int] = 5
  DEFAULT_INPUT_RATE: ClassVar[int] = 240
  # Enforce a minimum time before scrolling. Otherwise the page does not
  # fully load, the down/up scrolls do not end up in the same place, and
  # subsequent repetitions might accidentally trigger pull-to-refresh.
  MIN_LEAD_WAIT_TIME: ClassVar[dt.timedelta] = dt.timedelta(seconds=3)
  DEFAULT_LEAD_WAIT_TIME: ClassVar[dt.timedelta] = dt.timedelta(seconds=10)

  @property
  @override
  def story_name(self) -> str:
    return "scroll"

  @property
  def scroll_count(self) -> int:
    return self.config.scroll_count

  @property
  def input_rate(self) -> int:
    return self.config.input_rate

  def __init__(self,
               name_suffix: str,
               url: str,
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
    super().__init__(name_suffix, url, total_duration)

  @override
  def run(self, run: Run) -> None:
    if not run.browser_platform.is_android:
      raise RuntimeError(
          "The web-power-scroll benchmark is only supported on Android.")

    local_file = None
    remote_file = None

    try:
      with run.actions("Generate_Scrolls", verbose=True) as actions:
        display_res = run.browser_platform.display_resolution()
        evemu_data = generate_scroll_commands(self.config, display_res)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".evemu", delete=False) as f:
          f.write(evemu_data)
          local_file = pth.LocalPath(f.name)

      with run.actions("Push_Scrolls", verbose=True) as actions:
        remote_file = run.browser_platform.path(
            "/data/local/tmp/scrolling_sequence.evemu")
        run.browser_platform.push(local_file, remote_file)

      with run.actions("Lead_Wait", verbose=True) as actions:
        actions.show_url(self.url)
        actions.wait(self.lead_wait_time)

      with run.actions("Run", verbose=True):
        with run.actions("Scroll"):
          run.browser_platform.sh("uinput", f"{remote_file}")

    finally:
      if local_file is not None:
        local_file.unlink(missing_ok=True)
      if remote_file is not None:
        run.browser_platform.rm(remote_file, missing_ok=True)


class WebPowerScrollBenchmark(WebPowerBenchmarkBase):
  """Benchmark runner for Power Scroll scenario using legacy EVEMU emulation."""

  NAME: ClassVar = f"{WebPowerBenchmarkBase.NAME}-scroll"
  DEFAULT_STORY_CLS: ClassVar = WebPowerScrollStory

  @classmethod
  @override
  def add_cli_arguments(cls, parser: CBArgumentParser) -> CBArgumentParser:
    parser = super().add_cli_arguments(parser)
    story_cls = cls.DEFAULT_STORY_CLS
    default_lead_s = story_cls.DEFAULT_LEAD_WAIT_TIME.total_seconds()
    min_lead_s = story_cls.MIN_LEAD_WAIT_TIME.total_seconds()
    parser.add_argument(
        "--scrolls",
        "--scroll-count",
        dest="scroll_count",
        type=int,
        default=None,
        help="Number of times to repeat the up/down scroll sequence "
        f"(Default: {story_cls.DEFAULT_SCROLL_COUNT})")
    parser.add_argument(
        "--input-rate",
        "--rate",
        dest="input_rate",
        type=int,
        default=None,
        help="Frequency of synthetic scroll touch events in Hz. "
        f"(Default: {story_cls.DEFAULT_INPUT_RATE}Hz)")
    parser.add_argument(
        "--lead-wait-time",
        "--wait",
        dest="lead_wait_time",
        type=DurationParser.positive_or_zero_duration,
        default=story_cls.DEFAULT_LEAD_WAIT_TIME,
        help="Initial wait time after starting browser. Allow time to recover "
        "from the excitement of launching the browser. "
        f"(Default: {default_lead_s:.0f}s; Enforced minimum: {min_lead_s:.0f}s)"
    )
    return parser

  @classmethod
  @override
  def kwargs_from_cli(cls, args: argparse.Namespace) -> dict[str, Any]:
    kwargs = super().kwargs_from_cli(args)
    kwargs["scroll_count"] = args.scroll_count
    kwargs["input_rate"] = args.input_rate
    kwargs["lead_wait_time"] = args.lead_wait_time
    return kwargs
