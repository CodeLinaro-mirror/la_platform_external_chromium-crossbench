# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import datetime as dt
import logging
import sys
from threading import Thread
import time
from typing import (TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple,
                    Type)

import colorama

from crossbench.benchmarks.benchmark import Benchmark
from crossbench import cli_helper, helper
from crossbench.stories.story import Story

if TYPE_CHECKING:
  import argparse
  from crossbench.runner.run import Run


class ManualStory(Story, metaclass=abc.ABCMeta):

  STORY_NAME = "manual"

  def __init__(self, start_after: Optional[dt.timedelta],
               run_for: Optional[dt.timedelta]):
    self._start_after = start_after
    self._run_for = run_for
    self._start_time = dt.datetime.now()
    self._timer_thread = helper.RepeatTimer(interval=0.25, function=self._timer)
    duration = ((start_after or dt.timedelta()) +
                (run_for or dt.timedelta(seconds=30)))
    super().__init__(self.STORY_NAME, duration)

  def setup(self, run: Run) -> None:
    if self._start_after is None:
      logging.info("-" * 80)
      logging.critical("Press enter to start:")
      input()
    elif self._start_after.total_seconds():
      logging.critical("-" * 80)
      logging.critical(
          "The browser has launched. Measurement will start in %s" +
          " (or press enter to start immediately)", self._start_after)
      helper.input_with_timeout(timeout=self._start_after)
    logging.info("Starting Manual Benchmark...")
    self._start_time = dt.datetime.now()
    self._timer_thread.start()

  def run(self, run: Run) -> None:
    logging.info("-" * 80)
    try:
      self._wait_for_input()
      # Empty line to preserve timer output.
      print()
      logging.info("Stopping Manual Benchmark...")
    finally:
      self._timer_thread.cancel()

  def _wait_for_input(self) -> None:
    if self._run_for is None:
      logging.critical("Press enter to stop:")
      try:
        input()
      except KeyboardInterrupt:
        pass
    else:
      logging.critical(
          "Measurement has started. The browser will close in %s" +
          " (or press enter to close immediately)", self._run_for)
      helper.input_with_timeout(timeout=self._run_for)

  def _timer(self):
    delta = dt.datetime.now() - self._start_time
    indent = colorama.Cursor.FORWARD() * 3
    sys.stdout.write(f"{indent}Elapsed Time: {delta}\r")

  @classmethod
  def all_story_names(cls) -> Tuple[str, ...]:
    return (ManualStory.STORY_NAME,)


class ManualBenchmark(Benchmark, metaclass=abc.ABCMeta):
  """
  Benchmark runner for the manual mode.

  Just launches the browser and lets the user perform the desired interactions.
  Optionally waits for |start_after| seconds, then runs measurements for
  |run_for| seconds, then closes the browser.
  """
  NAME = "manual"
  DEFAULT_STORY_CLS = ManualStory

  def __init__(self, start_after, run_for) -> None:
    super().__init__([ManualStory(start_after=start_after, run_for=run_for)])

  @classmethod
  def add_cli_parser(
      cls, subparsers: argparse.ArgumentParser, aliases: Sequence[str] = ()
  ) -> cli_helper.CrossBenchArgumentParser:
    parser = super().add_cli_parser(subparsers, aliases)
    parser.add_argument(
        "--start-after",
        help="How long to wait until measurement starts",
        required=False,
        type=cli_helper.Duration.parse_zero)
    parser.add_argument(
        "--run-for",
        "--stop-after",
        "--duration",
        help="How long to run measurement for",
        required=False,
        type=cli_helper.Duration.parse_non_zero)
    return parser

  @classmethod
  def kwargs_from_cli(cls, args: argparse.Namespace) -> Dict[str, Any]:
    kwargs = super().kwargs_from_cli(args)
    kwargs["start_after"] = args.start_after
    kwargs["run_for"] = args.run_for
    return kwargs
