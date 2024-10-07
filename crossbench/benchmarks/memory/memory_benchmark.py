# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import logging
import sys
import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence, Type, Tuple

import selenium.common.exceptions
import urllib3.exceptions
from selenium import webdriver

from crossbench import helper
from crossbench.benchmarks.base import StoryFilter, SubStoryBenchmark
from crossbench.benchmarks.loading.action_runner.base import (
    ActionRunner, ActionRunnerListener)
from crossbench.benchmarks.loading.action_runner.basic_action_runner import \
    BasicActionRunner
from crossbench.benchmarks.loading.page import LivePage, Page
from crossbench.benchmarks.loading.tab_controller import TabController
from crossbench.browsers.webdriver import WebDriverBrowser
from crossbench.parse import NumberParser

if TYPE_CHECKING:
  import argparse

  from crossbench.cli.parser import CrossBenchArgumentParser
  from crossbench.runner.run import Run


class MemoryBenchmarkStoryFilter(StoryFilter[Page]):
  """
  Create memory story
  Specify alloc-count, block-size, compressiblity,
  prefill-constnat, random style to decide the
  memory workload.
  """
  stories: Sequence[Page]
  URL = "https://chromium-workloads.web.app/web-tests/main/synthetic/memory"

  @classmethod
  def add_cli_parser(
      cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser = super().add_cli_parser(parser)
    parser.add_argument(
        '--alloc-count',
        type=NumberParser.positive_int,
        default=1,
        help='The number of block to allocate.')
    parser.add_argument(
        '--block-size',
        type=NumberParser.positive_int,
        default=128,
        help='The size of each block (MB).')
    parser.add_argument(
        '--compressibility',
        type=NumberParser.positive_zero_int,
        default=0,
        help='The compressibility (0-100)')
    parser.add_argument(
        '--prefill-constant',
        type=NumberParser.any_int,
        default=1,
        help="Prefill memory buffer with given constant (-1-127)."
        "Default is 1."
        "-1 represents no prefilling.")
    parser.add_argument(
        "--random-per-buffer",
        dest="random_per_page",
        action="store_false",
        help="With the flag, it will generate the memory workload "
        "with random per buffer level. Without the flag,"
        "it will generate the memory workload with random"
        "per page level.")

    tab_group = parser.add_mutually_exclusive_group()
    tab_group.add_argument(
        "--tabs",
        type=TabController.parse,
        default=TabController.default(),
        help="Open memory workload in single/multiple/infinity tabs. "
        "Default is single."
        "Valid values are: 'single', 'inf', 'infinity', number")
    tab_group.add_argument(
        "--single-tab",
        dest="tabs",
        const=TabController.single(),
        default=TabController.default(),
        action="store_const",
        help="Open memory workload in a single tab."
        "Equivalent to --tabs=single")
    tab_group.add_argument(
        "--infinite-tab",
        dest="tabs",
        const=TabController.forever(),
        action="store_const",
        help="Open memory workload in seperate tabs infinitely."
        "Equivalent to --tabs=infinity")
    return parser

  @classmethod
  def kwargs_from_cli(cls, args: argparse.Namespace) -> Dict[str, Any]:
    kwargs = super().kwargs_from_cli(args)
    kwargs["args"] = args
    return kwargs

  def __init__(self,
               story_cls: Type[Page],
               patterns: Sequence[str],
               args: argparse.Namespace,
               separate: bool = False) -> None:
    self._args: argparse.Namespace = args

    super().__init__(story_cls, patterns, separate)

  def process_all(self, patterns: Sequence[str]) -> None:
    super().process_all(patterns)
    self.stories = self.stories_from_cli_args(self._args)

  @classmethod
  def stories_from_cli_args(cls, args: argparse.Namespace) -> Sequence[Page]:
    url_params = {
        "alloc": str(args.alloc_count),
        "blocksize": str(args.block_size),
        "compress": str(args.compressibility),
        "prefill": str(args.prefill_constant),
    }
    if not args.random_per_page:
      url_params["randomperpage"] = "false"
    url = helper.update_url_query(cls.URL, url_params)
    stories: Sequence[Page] = []
    page = LivePage("memory", url, dt.timedelta(seconds=2), tabs=args.tabs)
    stories = [page]
    return stories

  def create_stories(self, separate: bool) -> Sequence[Page]:
    logging.info("SELECTED STORIES: %s", ", ".join(map(str, self.stories)))
    return self.stories


class MemoryBenchmark(ActionRunnerListener, SubStoryBenchmark):
  """
  Benchmark runner for memory stress test.
  """

  NAME = "memory"
  DEFAULT_STORY_CLS = Page
  STORY_FILTER_CLS = MemoryBenchmarkStoryFilter

  @classmethod
  def add_cli_parser(
      cls, subparsers: argparse.ArgumentParser, aliases: Sequence[str] = ()
  ) -> CrossBenchArgumentParser:
    parser = super().add_cli_parser(subparsers, aliases)
    cls.STORY_FILTER_CLS.add_cli_parser(parser)
    parser.add_argument(
        '--skippable-tab-count',
        dest="skippable_tab_count",
        type=NumberParser.positive_int,
        default=0,
        help='The number of tabs that can be skipped for liveness checking.')
    return parser

  @classmethod
  def kwargs_from_cli(cls, args: argparse.Namespace) -> Dict[str, Any]:
    kwargs = super().kwargs_from_cli(args)
    kwargs["skippable_tab_count"] = args.skippable_tab_count
    return kwargs

  @classmethod
  def stories_from_cli_args(cls, args: argparse.Namespace) -> Sequence[Page]:
    super().stories_from_cli_args(args)
    stories = MemoryBenchmarkStoryFilter.stories_from_cli_args(args)
    return stories

  @classmethod
  def all_story_names(cls) -> Tuple[str, ...]:
    return ()

  def __init__(self,
               stories: Sequence[Page],
               skippable_tab_count: Optional[int] = 0,
               action_runner: Optional[ActionRunner] = None) -> None:
    self._action_runner = action_runner or BasicActionRunner()
    for story in stories:
      assert isinstance(story, Page)
    super().__init__(stories)
    # Records the navigation_starttime time for each window handle.
    self.navigation_time_ms: Dict[str, float] = {}
    self.tab_count: int = 1
    self.skippable_tab_count = skippable_tab_count
    self._action_runner.set_listener(self)

  @classmethod
  def describe(cls) -> Dict[str, Any]:
    data = super().describe()
    data["url"] = cls.STORY_FILTER_CLS.URL
    return data

  @property
  def action_runner(self) -> ActionRunner:
    return self._action_runner

  def get_driver(self, run: Run) -> webdriver.Remote:
    if isinstance(run.browser, WebDriverBrowser):
      return run.browser.driver
    raise TypeError("Memory benchmark only supports WebDriverBrowser.")

  def _increment_tab_count(self):
    self.tab_count += 1

  def _record_navigation_time(self, run: Run) -> None:
    """
    Record NavigationStart time for each handle.
    """
    driver = self.get_driver(run)
    cur_handle: str = driver.current_window_handle

    navigation_starttime = driver.execute_script(
        "return window.performance.timing.navigationStart")
    logging.debug("Navigation starttime for handle %s is %s.", cur_handle,
                  navigation_starttime)
    self.navigation_time_ms[cur_handle] = navigation_starttime

  def _check_liveness(self, run: Run) -> None:
    """
    Navigate each opened tab, and check if the navigation start time
    has changed. If so, then it means that page has been discarded
    and reloaded.
    """
    driver = self.get_driver(run)
    for handle in self.navigation_time_ms:
      logging.debug("Liveness checking for handle: %s", handle)
      driver.switch_to.window(handle)
      time.sleep(1)
      navigation_starttime = driver.execute_script(
          "return window.performance.timing.navigationStart")

      if navigation_starttime != self.navigation_time_ms[handle]:
        logging.debug("Found a page that has been reloaded!")
        logging.info(
            "The max num of tabs we can keep alive concurrently is: %s ",
            self.tab_count - 1)
        sys.exit()

  def handle_error(self, e: Exception) -> None:
    """
    If there is a page crash error or a http request time out
    for the stress liveness test, directly exit the benchmark
    and report the max alive tab count.
    """
    if isinstance(e, selenium.common.exceptions.WebDriverException
                 ) and "page crash" in str(e) or isinstance(
                     e, urllib3.exceptions.ReadTimeoutError):
      logging.debug("Crash/Timeout found: %s ", e)
      logging.info("The max num of tabs we can keep alive concurrently is: %s ",
                   self.tab_count - 1)
      # TODO: Check if there is a better way to exit the benchmark.
      sys.exit()

  def handle_page_run(self, run: Run) -> None:
    self._record_navigation_time(run)
    if self.tab_count > self.skippable_tab_count:
      self._check_liveness(run)

  def handle_new_tab(self) -> None:
    self._increment_tab_count()
