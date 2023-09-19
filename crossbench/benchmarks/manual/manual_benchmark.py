# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import datetime as dt
import logging
from threading import Thread
import time
from typing import (TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple,
                    Type)

from crossbench.benchmarks.benchmark import Benchmark
from crossbench import cli_helper
from crossbench.stories.story import Story

if TYPE_CHECKING:
  import argparse
  from crossbench.runner.run import Run


class ManualStory(Story, metaclass=abc.ABCMeta):

  STORY_NAME = "manual"

  def __init__(self, start_after: dt.timedelta, run_for: dt.timedelta):
    self._start_after = start_after
    self._run_for = run_for
    super().__init__(self.STORY_NAME, start_after + run_for)

  def setup(self, run: Run) -> None:
    logging.critical("The browser has launched. Measurement will start in %s" +
                     " (or press enter to start immediately)",
                     self._start_after)
    wait = Thread(target=input)
    wait.start()
    wait.join(timeout=self._start_after.total_seconds())

  def run(self, run: Run) -> None:
    logging.critical("Measurement has started. The browser will close in %s" +
                     " (or press enter to close immediately)",
                     self._run_for)
    wait = Thread(target=input)
    wait.start()
    wait.join(timeout=self._run_for.total_seconds())

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
        default=dt.timedelta(seconds=0),
        type=cli_helper.Duration.parse_zero)
    parser.add_argument(
        "--run-for",
        help="How long to run measurement for",
        default=dt.timedelta(seconds=30),
        type=cli_helper.Duration.parse_non_zero)
    return parser

  @classmethod
  def kwargs_from_cli(cls, args: argparse.Namespace) -> Dict[str, Any]:
    kwargs = super().kwargs_from_cli(args)
    kwargs["start_after"] = args.start_after
    kwargs["run_for"] = args.run_for
    return kwargs
