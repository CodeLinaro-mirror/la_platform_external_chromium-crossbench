# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pytype: disable=attribute-error

from __future__ import annotations

import abc
import argparse
import datetime as dt
from typing import Sequence

from typing_extensions import override

from crossbench.action_runner.default_action_runner import DefaultActionRunner
from crossbench.benchmarks.loading.loadline_presets import (
    LoadLinePageFilter, LoadLinePhoneBenchmark, LoadLineTabletBenchmark)
from crossbench.benchmarks.loading.playback_controller import \
    PlaybackController
from crossbench.benchmarks.loading.tab_controller import TabController
from tests import test_helper
from tests.crossbench.base import BaseCliTestCase
from tests.crossbench.benchmarks.helper import SubStoryTestCase


# TODO(378584786): use shared helper mixin with TestPageLoadBenchmark
class BaseLoadLineBenchmarkTestCase(SubStoryTestCase, metaclass=abc.ABCMeta):

  @override
  def setUp(self):
    super().setUp()
    self.setup_loadline_config()

  @override
  def story_filter(  # pylint: disable=arguments-differ
      self,
      patterns: Sequence[str],
      separate: bool = True,
  ) -> LoadLinePageFilter:
    args = argparse.Namespace(
        about_blank_duration=dt.timedelta(),
        playback=PlaybackController.default(),
        tabs=TabController.default(),
        action_runner=DefaultActionRunner(),
        run_login=True,
        run_setup=True)
    story_filter = super().story_filter(patterns, args=args, separate=separate)
    assert isinstance(story_filter, LoadLinePageFilter)
    return story_filter

  def test_all_stories(self):
    # TODO: preload the story names from the config files
    stories = self.story_filter(["all"]).stories
    self.assertFalse(stories)

  def test_default_stories(self):
    # TODO: preload the story names from the config files
    stories = self.story_filter(["default"]).stories
    self.assertFalse(stories)

  def test_get_pages_config(self):
    config = self.benchmark_cls.get_pages_config()
    # Ensure it's cached
    self.assertIs(config, self.benchmark_cls.get_pages_config())

  def test_get_pages_config_variants(self):
    configs = [
        LoadLineTabletBenchmark.get_pages_config(),
        LoadLinePhoneBenchmark.get_pages_config()
    ]
    self.assertNotEqual(configs[0], configs[1])


class TestLoadLineTabletBenchmark(BaseLoadLineBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self):
    return LoadLineTabletBenchmark


class TestLoadLinePhoneBenchmark(BaseLoadLineBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self):
    return LoadLinePhoneBenchmark


class LoadLineBenchmarkCliTestCase(BaseCliTestCase):

  def test_run_default_phone(self):
    # TODO(378584786): implement
    pass

  def test_run_default_tablet(self):
    # TODO(378584786): implement
    pass


# Don't expose abstract base test cases.
del BaseLoadLineBenchmarkTestCase
del BaseCliTestCase
del SubStoryTestCase

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
