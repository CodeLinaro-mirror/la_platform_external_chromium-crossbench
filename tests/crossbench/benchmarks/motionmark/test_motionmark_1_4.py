# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import copy
import csv
from unittest import mock

from typing_extensions import override

from crossbench.benchmarks.motionmark.motionmark_1_4 import \
    MotionMark14Benchmark, MotionMark14Probe, MotionMark14ProbeContext, \
    MotionMark14Story
from crossbench.env.runner_env import EnvConfig, RunnerEnv, ValidationMode
from crossbench.runner.runner import Runner
from tests import test_helper
from tests.crossbench.benchmarks.motionmark.helper import \
    MotionMark1BaseTestCase


class MotionMark14TestCase(MotionMark1BaseTestCase):

  EXAMPLE_PROBE_DATA = [{
      "testsResults": {
          "MotionMark": {
              "Stories": {
                  "complexity": {
                      "complexity":
                          1169.7666313745012,
                      "stdev":
                          2.6693101402239985,
                      "bootstrap": {
                          "confidenceLow": 1154.0859381321234,
                          "confidenceHigh": 1210.464520355893,
                          "median": 1180.8987652049277,
                          "mean": 1163.0061487765158,
                          "confidencePercentage": 0.8
                      },
                      "segment1": [[1, 16.666666666666668],
                                   [1, 16.666666666666668]],
                      "segment2": [[1, 6.728874992470971],
                                   [3105, 13.858528114770454]]
                  },
                  "controller": {
                      "score": 1168.106104032434,
                      "average": 1168.106104032434,
                      "stdev": 37.027504395081785,
                      "percent": 3.1698750881669624
                  },
                  "score": 1180.8987652049277,
                  "scoreLowerBound": 1154.0859381321234,
                  "scoreUpperBound": 1210.464520355893
              }
          }
      },
      "score": 1180.8987652049277,
      "scoreLowerBound": 1154.0859381321234,
      "scoreUpperBound": 1210.464520355893
  }]

  @property
  @override
  def benchmark_cls(self):
    return MotionMark14Benchmark

  @property
  @override
  def story_cls(self):
    return MotionMark14Story

  @property
  @override
  def probe_cls(self):
    return MotionMark14Probe

  @property
  @override
  def probe_context_cls(self):
    return MotionMark14ProbeContext

  @override
  def _test_run(self, custom_url: str | None = None, throw: bool = False):
    stories = self.story_cls.from_names(["Stories"], url=custom_url)
    repetitions = 3
    for _ in range(repetitions):
      for _ in stories:
        for browser in self.browsers:
          browser.expect_js(result=True)
          browser.expect_js(result=True)
          browser.expect_js(result=1)
          browser.expect_js()
          browser.expect_js(result=True)
          browser.expect_js(result=self.EXAMPLE_PROBE_DATA)
    for browser in self.browsers:
      browser.expected_js = copy.deepcopy(browser.expected_js)
    benchmark = self.benchmark_cls(stories, custom_url=custom_url)
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
    with mock.patch.object(RunnerEnv, "validate_url", return_value=True) as cm:
      runner.run()
    cm.assert_called_once()
    assert runner.is_success
    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertEqual(len(urls), repetitions)
      self.assertTrue(browser.was_js_invoked(self.probe_context_cls.JS))
    with (self.out_dir /
          f"{self.probe_cls.NAME}.csv").open(encoding="utf-8") as f:
      csv_data = list(csv.DictReader(f, delimiter="\t"))
    self.assertListEqual(
        list(csv_data[0].keys()), ["label", "", "dev", "stable"])
    self.assertDictEqual(
        csv_data[1], {
            "label": "version",
            "dev": "102.22.33.44",
            "stable": "100.22.33.44",
            "": "",
        })


del MotionMark1BaseTestCase

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
