# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import argparse
from typing import TYPE_CHECKING, Optional, Sequence, Tuple

from crossbench import path as pth
from crossbench.benchmarks.loading.config.pages import PagesConfig
from crossbench.benchmarks.loading.loading_benchmark import (LoadingPageFilter,
                                                             PageLoadBenchmark)
from crossbench.flags.base import Flags

if TYPE_CHECKING:
  from crossbench.benchmarks.loading.page import Page
  from crossbench.browsers.browser import Browser

CONFIG_DIR = pth.LocalPath(__file__).parents[3] / "config"
LOADING_DIR = CONFIG_DIR / "benchmark" / "loading"


class PresetLoadingPageFilter(LoadingPageFilter):
  """Page Load benchmark for phone/tablet."""
  CAN_COMBINE_STORIES: bool = False

  @classmethod
  def add_page_config_parser(cls, parser: argparse.ArgumentParser) -> None:
    pass

  @classmethod
  def default_stories(cls) -> Tuple[Page, ...]:
    return cls.all_stories()

  @classmethod
  def all_stories(cls) -> Tuple[Page, ...]:
    return ()


class PresetPageLoadBenchmark(PageLoadBenchmark, metaclass=abc.ABCMeta):
  STORY_FILTER_CLS = PresetLoadingPageFilter

  @classmethod
  def cli_description(cls) -> str:
    return cls.__doc__.strip()

  @classmethod
  def requires_separate(cls, args: argparse.Namespace):
    # Perfetto metrics used in the benchmark require a separate Perfetto
    # session for each run.
    return True

  @classmethod
  def default_probe_config_path(cls) -> pth.LocalPath:
    return pth.LocalPath(LOADING_DIR) / "probe_config.hjson"

  @classmethod
  @abc.abstractmethod
  def default_network_config_path(cls) -> pth.LocalPath:
    pass

  @classmethod
  @abc.abstractmethod
  def default_pages_config_path(cls) -> pth.LocalPath:
    pass

  @classmethod
  def get_pages_config(
      cls, args: Optional[argparse.Namespace] = None) -> PagesConfig:
    return PagesConfig.parse(cls.default_pages_config_path())

  @classmethod
  def all_story_names(cls) -> Sequence[str]:
    return tuple(page.label for page in cls.get_pages_config().pages)


class PageLoadTabletBenchmark(PresetPageLoadBenchmark):
  """Page Load benchmark for tablet.
  """
  NAME = "loading-tablet"

  @classmethod
  def default_pages_config_path(cls) -> pth.LocalPath:
    return pth.LocalPath(LOADING_DIR) / "page_config_tablet.hjson"

  @classmethod
  def default_network_config_path(cls) -> pth.LocalPath:
    return pth.LocalPath(LOADING_DIR) / "network_config_tablet.hjson"

  @classmethod
  def aliases(cls) -> Tuple[str, ...]:
    return ("load-tablet", "ld-tablet")

  @classmethod
  def extra_flags(cls, browser: Browser) -> Flags:
    assert browser.attributes.is_chromium_based
    return Flags(["--request-desktop-sites"])


class PageLoadPhoneBenchmark(PresetPageLoadBenchmark):
  """Page Load benchmark for phones.
  """
  NAME = "loading-phone"

  @classmethod
  def default_pages_config_path(cls) -> pth.LocalPath:
    return pth.LocalPath(LOADING_DIR) / "page_config_phone.hjson"

  @classmethod
  def default_network_config_path(cls) -> pth.LocalPath:
    return pth.LocalPath(LOADING_DIR) / "network_config_phone.hjson"

  @classmethod
  def aliases(cls) -> Tuple[str, ...]:
    return ("load-phone", "ld-phone")
