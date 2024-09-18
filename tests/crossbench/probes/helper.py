# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
import json
from typing import Any, Callable, Iterable, List, Sequence, Tuple, Union

from crossbench.benchmarks.loading.loading_benchmark import PageLoadBenchmark
from crossbench.benchmarks.loading.page import CombinedPage, Page
from crossbench.env import HostEnvironmentConfig, ValidationMode
from crossbench.probes.probe import Probe
from crossbench.runner.runner import Runner
from tests.crossbench.base import BaseCrossbenchTestCase


class GenericProbeTestCase(BaseCrossbenchTestCase):

  def create_runner(self,
                    stories: Sequence[Page],
                    js_side_effects: Union[List[Any], Callable[[Page],
                                                               List[Any]]],
                    separate: bool = False,
                    repetitions: int = 3,
                    warmup_repetitions: int = 0,
                    cache_temperatures: Iterable[str] = ("default",),
                    throw: bool = True) -> Runner:
    self.assertTrue(stories)
    if not separate and len(stories) > 1:
      stories = [CombinedPage(stories)]
    if isinstance(js_side_effects, list):
      js_side_effects_fn = lambda story: js_side_effects
    else:
      js_side_effects_fn = js_side_effects
    # The order should match Runner.get_runs
    for _ in range(warmup_repetitions + repetitions):
      for story in stories:
        story_js_side_effects = js_side_effects_fn(story)
        for browser in self.browsers:
          for js_result in story_js_side_effects:
            browser.expect_js(result=js_result)

    for browser in self.browsers:
      browser.expected_js = copy.deepcopy(browser.expected_js)

    benchmark = PageLoadBenchmark(stories)  # pytype: disable=not-instantiable
    self.assertTrue(len(benchmark.describe()) > 0)
    runner = Runner(
        self.out_dir,
        self.browsers,
        benchmark,
        env_config=HostEnvironmentConfig(),
        env_validation_mode=ValidationMode.SKIP,
        platform=self.platform,
        repetitions=repetitions,
        warmup_repetitions=warmup_repetitions,
        cache_temperatures=cache_temperatures,
        throw=throw)
    return runner

  def get_non_empty_json_results(self, runner: Runner,
                                probe: Probe) -> Tuple[Any, Any, Any, Any]:
    story_json_file = runner.runs[0].results[probe].json
    with story_json_file.open() as f:
      story_json_data = json.load(f)
    self.assertIsNotNone(story_json_data)

    repetitions_json_file = runner.repetitions_groups[0].results[probe].json
    with repetitions_json_file.open() as f:
      repetitions_json_data = json.load(f)
    self.assertIsNotNone(repetitions_json_data)

    stories_json_file = runner.story_groups[0].results[probe].json
    with stories_json_file.open() as f:
      stories_json_data = json.load(f)
    self.assertIsNotNone(stories_json_data)

    browsers_json_file = runner.browser_group.results[probe].json
    with browsers_json_file.open() as f:
      browsers_json_data = json.load(f)
    self.assertIsNotNone(browsers_json_data)
    return (story_json_data, repetitions_json_data, stories_json_data,
            browsers_json_data)

  def get_non_empty_results_str(
      self,
      runner: Runner,
      probe: Probe,
      suffix: str,
      has_browsers_data: bool = True) -> Tuple[str, str, str, str]:
    story_file = runner.runs[0].results[probe].get_all(suffix)[0]
    story_data = story_file.read_text()
    self.assertTrue(story_data)

    repetitions_file = runner.repetitions_groups[0].results[probe].get_all(
        suffix)[0]
    repetitions_data = repetitions_file.read_text()
    self.assertTrue(repetitions_data)

    stories_file = runner.story_groups[0].results[probe].get_all(suffix)[0]
    stories_data = stories_file.read_text()
    self.assertTrue(stories_data)

    if has_browsers_data:
      browsers_file = runner.browser_group.results[probe].get_all(suffix)[0]
      browsers_data = browsers_file.read_text()
      self.assertTrue(browsers_data)
    else:
      browsers_data = ""

    return (story_data, repetitions_data, stories_data, browsers_data)
