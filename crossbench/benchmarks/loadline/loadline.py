# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import argparse
import logging
from typing import TYPE_CHECKING, Mapping, Optional, Sequence

import pandas as pd
from tabulate import tabulate
from typing_extensions import override

from crossbench import path as pth
from crossbench.benchmarks.benchmark_probe import BenchmarkProbeMixin
from crossbench.benchmarks.loading.config.pages import PagesConfig
from crossbench.benchmarks.loading.loading_benchmark import (LoadingBenchmark,
                                                             LoadingPageFilter)
from crossbench.probes.probe import Probe
from crossbench.probes.results import LocalProbeResult

if TYPE_CHECKING:
  from crossbench.benchmarks.loading.page.base import Page
  from crossbench.browsers.attributes import BrowserAttributes
  from crossbench.probes.results import ProbeResult
  from crossbench.runner.groups.browsers import BrowsersRunGroup


class LoadLineProbe(BenchmarkProbeMixin, Probe):
  IS_GENERAL_PURPOSE = False
  BENCHMARK_NAME: str = "LoadLine"
  BENCHMARK_VERSION: str = ""

  @override
  def log_browsers_result(self, group: BrowsersRunGroup) -> None:
    logging.info("-" * 80)
    logging.critical("%s Benchmark (%s)", self.BENCHMARK_NAME,
                     self.BENCHMARK_VERSION)
    logging.critical("%s results:", self.BENCHMARK_NAME)
    logging.info("- " * 40)
    logging.critical(
        tabulate(
            pd.read_csv(
                group.get_local_probe_result_path(self).with_suffix(".csv")),
            headers="keys",
            tablefmt="plain"))

  @override
  def merge_browsers(self, group: BrowsersRunGroup) -> ProbeResult:
    csv_file = group.get_local_probe_result_path(self).with_suffix(".csv")
    self._compute_score(group).to_csv(csv_file)
    return LocalProbeResult(csv=(csv_file,))

  @abc.abstractmethod
  def _compute_score(self, group: BrowsersRunGroup) -> pd.DataFrame:
    pass


class LoadLinePageFilter(LoadingPageFilter):
  """LoadLine benchmark for phone/tablet."""
  @classmethod
  def add_page_config_parser(cls, parser: argparse.ArgumentParser) -> None:
    page_config_group = parser.add_mutually_exclusive_group()
    cls.add_page_config_arguments(page_config_group)

  @classmethod
  def _add_story_grouping_arguments(cls,
                                    parser: argparse.ArgumentParser) -> None:
    # Loadline always needs separate substories for metrics calculation.
    parser.add_argument(
        "--separate",
        action="store_true",
        default=True,
        help="Run each story in a fresh browser (enabled by default).")

  @classmethod
  @override
  def default_stories(cls) -> tuple[Page, ...]:
    return cls.all_stories()

  @classmethod
  @override
  def all_stories(cls) -> tuple[Page, ...]:
    return tuple()


class LoadLineBenchmark(LoadingBenchmark, metaclass=abc.ABCMeta):
  STORY_FILTER_CLS = LoadLinePageFilter

  _page_config: PagesConfig | None = None

  @classmethod
  @abc.abstractmethod
  @override
  def default_probe_config_path(cls) -> pth.LocalPath:
    pass

  @classmethod
  @abc.abstractmethod
  @override
  def default_network_config_path(cls) -> pth.LocalPath:
    pass

  @classmethod
  @abc.abstractmethod
  def default_pages_config_path(cls) -> pth.LocalPath:
    pass

  @classmethod
  @override
  def get_pages_config(
      cls, args: Optional[argparse.Namespace] = None) -> PagesConfig:
    # Use manual caching, since args is not hashable.
    if not args or not args.pages_config:
      if cls._page_config is None:
        cls._page_config = PagesConfig.parse(cls.default_pages_config_path())
      return cls._page_config
    if args.config:
      raise argparse.ArgumentTypeError(
          "--config is not supported with loadline.")
    return args.pages_config

  @classmethod
  @override
  def describe_stories(cls) -> Mapping[str, str]:
    # TODO: Use full story objects
    result: dict[str, str] = {}
    for page_config in cls.get_pages_config().pages:
      result[page_config.any_label] = page_config.first_url
    return result

  @classmethod
  @override
  def all_story_names(cls) -> Sequence[str]:
    return tuple(page.any_label for page in cls.get_pages_config().pages)
