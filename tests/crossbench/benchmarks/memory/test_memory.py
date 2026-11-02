# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import argparse
import csv
from typing import TYPE_CHECKING
import unittest.mock

from typing_extensions import override

import crossbench.benchmarks.memory.memory_benchmark as mb
from crossbench import path as pth
from crossbench.benchmarks.loading.page.live import LivePage
from crossbench.benchmarks.loading.playback_controller import \
    PlaybackController
from crossbench.benchmarks.loading.tab_controller import TabController
from crossbench.benchmarks.memory.memory_benchmark import MemoryBenchmark, \
    MemoryBenchmarkStoryFilter, MemoryProbe
from crossbench.env.runner_env import EnvConfig, ValidationMode
from crossbench.runner.runner import Runner
from tests import test_helper
from tests.crossbench.benchmarks import helper
from tests.crossbench.mock_browser import JsInvocation

if TYPE_CHECKING:
  from tests.crossbench.mock_browser import MockBrowser


class MemoryBenchmarkTestCase(helper.BaseBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self):
    return MemoryBenchmark

  @property
  @override
  def story_cls(self):
    return MemoryBenchmarkStoryFilter

  @property
  def probe_cls(self):
    return MemoryProbe

  def _create_stories(self, tab_count):
    args = argparse.Namespace(
        alloc_count=8,
        prefill_constant=8,
        compressibility=50,
        random_per_page=False,
        block_size=128,
        memory_percent=2.0,
        skip_liveness_checks_until=40,
        playback=PlaybackController.default(),
        tabs=TabController.repeat(tab_count),
        action_runner_config=None)
    stories = self.story_cls.stories_from_cli_args(args=args)
    return stories

  def test_story(self):
    stories = self._create_stories(tab_count=2)
    self.assertEqual(len(stories), 1)
    story = stories[0]
    self.assertIsInstance(story, LivePage)
    expected_url = "about:blank"
    self.assertEqual(story.first_url, expected_url)
    names = {story.name for story in stories}
    self.assertEqual(len(names), len(stories))

  def test_run_throw(self):
    self._test_run(throw=True)

  def test_run_default(self):
    self._test_run()

  def _expect_tab_js(self, browser: MockBrowser, tab_index: int) -> None:
    # Inject alloc.js payload.
    browser.expect_js(JsInvocation(None, "/* alloc */"))
    # Record navigation start and performance mark timestamps.
    browser.expect_js(
        JsInvocation(1000.0 + tab_index,
                     "return window.performance.timing.navigationStart"))
    browser.expect_js(
        JsInvocation(
            100.0, "return performance.getEntriesByName("
            f"'page-loaded~{tab_index}')[0].startTime"))
    browser.expect_js(
        JsInvocation(
            200.0, "return performance.getEntriesByName("
            f"'allocation-start~{tab_index}')[0].startTime"))
    browser.expect_js(
        JsInvocation(
            350.0, "return performance.getEntriesByName("
            f"'allocation-done~{tab_index}')[0].startTime"))
    browser.expect_js(
        JsInvocation(
            None, "performance.mark('crossbench_tab_timing', { detail: {"
            f" tab_index: {tab_index}, page_load_duration_ms: 100.0,"
            " allocation_duration_ms: 150.0 } })"))
    # Record alive tabs count (liveness check skipped while tab_count <= 40).
    browser.expect_js(
        JsInvocation(
            None, "performance.mark('tabs_alive', { detail: {"
            f" tab_index: {tab_index}, alive_count: {tab_index + 1} }} }})"))

  def _test_run(self, throw: bool = False) -> None:
    tab_count = 2
    repetitions = 2
    stories = self._create_stories(tab_count=tab_count)
    for browser in self.browsers:
      for _ in range(repetitions):
        for _ in stories:
          for tab_index in range(tab_count):
            self._expect_tab_js(browser, tab_index)

    benchmark = self.benchmark_cls(stories)
    self.assertTrue(len(benchmark.describe()) > 0)
    runner = Runner(
        self.out_dir,
        self.browsers,
        benchmark,
        env_config=EnvConfig(),
        env_validation_mode=ValidationMode.SKIP,
        platform=self.platform,
        repetitions=repetitions,
        throw=throw,
        in_memory_result_db=True)

    self.fs.create_file(
        pth.LocalPath(mb.__file__).parent / "scripts" / "alloc.js",
        contents="/* alloc */")

    with unittest.mock.patch(
        "crossbench.plt.base.Platform.system_memory_bytes",
        new_callable=unittest.mock.PropertyMock,
        return_value=16 * 1024 * 1024 * 1024), \
        unittest.mock.patch(
            "crossbench.browsers.browser.Browser.switch_window"), \
        unittest.mock.patch(
            "crossbench.browsers.browser.Browser.close_all_tabs"):
      runner.run()
    assert runner.is_success
    for browser in self.browsers:
      self.assertFalse(browser.expected_js)

    with (self.out_dir /
          f"{self.probe_cls.NAME}.csv").open(encoding="utf-8") as f:
      csv_data = list(csv.DictReader(f, delimiter="\t"))
    self.assertSequenceEqual(
        list(csv_data[0].keys()), ["label", "", "dev", "stable"])
    self.assertDictEqual(
        csv_data[1],
        {
            "label": "version",
            "dev": "102.22.33.44",
            "stable": "100.22.33.44",
            # One padding element (after "label"):
            "": "",
        })

    with self.assertLogs(level="INFO") as cm:
      for probe in runner.probes:
        for run in runner.runs:
          probe.log_run_result(run)
    output = "\n".join(cm.output)
    self.assertIn("Memory results", output)
    self.assertIn(f"Scores [{tab_count}]", output)

    with self.assertLogs(level="INFO") as cm:
      for probe in runner.probes:
        probe.log_browsers_result(runner.browser_group)
    output = "\n".join(cm.output)
    self.assertIn("Memory results", output)
    self.assertIn("102.22.33.44", output)
    self.assertIn("100.22.33.44", output)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
