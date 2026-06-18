# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING
from unittest import mock

from typing_extensions import override

from crossbench.benchmarks.blink_ai.blink_ai import BlinkAIBenchmark, \
    BlinkAIStory
from crossbench.benchmarks.blink_ai.probe import BlinkAIProbe, \
    BlinkAIProbeContext
from crossbench.env.runner_env import EnvConfig, ValidationMode
from crossbench.runner.runner import Runner
from tests import test_helper
from tests.crossbench.benchmarks import helper

if TYPE_CHECKING:
  from tests.crossbench.mock_browser import MockBrowser


class BlinkAITestCase(helper.SubStoryTestCase):

  @property
  @override
  def benchmark_cls(self):
    return BlinkAIBenchmark

  @property
  @override
  def story_cls(self):
    return BlinkAIStory

  @property
  def probe_cls(self):
    return BlinkAIProbe

  @property
  def probe_context_cls(self):
    return BlinkAIProbeContext

  def _setup_run_js_expect(self,
                           browser: MockBrowser,
                           probe_results: dict,
                           status: str = "success") -> None:
    # wait_js_condition for window.LanguageModel
    browser.expect_js(result=True)
    # JS click for #start-button
    browser.expect_js(result=None)
    # wait_js_condition for window.testStatus !== 'running'
    browser.expect_js(result=True)
    # window.testStatus check
    browser.expect_js(result=status)
    if status == "success":
      # window.metrics check in story run()
      browser.expect_js(result=probe_results)
    # window.metrics in probe (JsonResultProbeContext)
    browser.expect_js(result=json.dumps(probe_results))

  def test_run_default(self):
    # Prepare stories
    stories = self.story_cls.from_names(["language_model"])
    benchmark = self.benchmark_cls(stories)
    self.assertTrue(len(benchmark.describe()) > 0)

    # Set up expectations for mock browsers
    probe_results = {
        "downloadTimeMs": 500.5,
        "sessionCreationTimeMs": 120.5,
        "coldTimeToFirstTokenMs": 45.2,
        "coldTotalPromptTimeMs": 250.0,
        "coldChunksPerSecond": 45.8,
        "warmTimeToFirstTokenMs": [12.5, 10.2, 9.8],
        "warmTotalPromptTimeMs": [110.0, 95.0, 92.0],
        "warmChunksPerSecond": [50.2, 55.1, 56.3]
    }

    repetitions = 2
    for _ in range(repetitions):
      for browser in self.browsers:
        self._setup_run_js_expect(browser, probe_results)

    for browser in self.browsers:
      browser.expected_js = copy.deepcopy(browser.expected_js)

    runner = Runner(
        self.out_dir,
        self.browsers,
        benchmark,
        env_config=EnvConfig(),
        env_validation_mode=ValidationMode.SKIP,
        platform=self.platform,
        repetitions=repetitions,
        throw=True,
        in_memory_result_db=True)

    with mock.patch.object(self.benchmark_cls, "validate_url") as cm:
      runner.run()
    cm.assert_called_once()

    # Verification
    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertEqual(len(urls), repetitions)
      self.assertIn(self.story_cls.URL + "?stories=language_model", urls)
      self.assertListEqual(browser.expected_js, [])
  def test_run_custom_url(self):
    custom_url = "http://test.example.com/blink_ai"
    stories = self.story_cls.from_names(["language_model"], url=custom_url)
    benchmark = self.benchmark_cls(stories)

    probe_results = {
        "downloadTimeMs": 0.0,
        "sessionCreationTimeMs": 100.0,
        "coldTimeToFirstTokenMs": 40.0,
        "coldTotalPromptTimeMs": 200.0,
        "coldChunksPerSecond": 50.0,
        "warmTimeToFirstTokenMs": [10.0],
        "warmTotalPromptTimeMs": [90.0],
        "warmChunksPerSecond": [55.0]
    }
    repetitions = 1
    for _ in range(repetitions):
      for browser in self.browsers:
        self._setup_run_js_expect(browser, probe_results)

    for browser in self.browsers:
      browser.expected_js = copy.deepcopy(browser.expected_js)

    runner = Runner(
        self.out_dir,
        self.browsers,
        benchmark,
        env_config=EnvConfig(),
        env_validation_mode=ValidationMode.SKIP,
        platform=self.platform,
        repetitions=repetitions,
        throw=True,
        in_memory_result_db=True)

    with mock.patch.object(self.benchmark_cls, "validate_url") as cm:
      runner.run()
    cm.assert_called_once()

    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertEqual(len(urls), repetitions)
      self.assertIn(custom_url + "?stories=language_model", urls)
      self.assertListEqual(browser.expected_js, [])

  def test_run_error(self):
    stories = self.story_cls.from_names(["language_model"])
    benchmark = self.benchmark_cls(stories)

    probe_results = {}
    repetitions = 1
    active_browsers = self.browsers[:1]
    for _ in range(repetitions):
      for browser in active_browsers:
        self._setup_run_js_expect(browser, probe_results, status="failed")

    for browser in active_browsers:
      browser.expected_js = copy.deepcopy(browser.expected_js)

    runner = Runner(
        self.out_dir,
        active_browsers,
        benchmark,
        env_config=EnvConfig(),
        env_validation_mode=ValidationMode.SKIP,
        platform=self.platform,
        repetitions=repetitions,
        throw=True,
        in_memory_result_db=True)

    with mock.patch.object(self.benchmark_cls, "validate_url") as cm:
      with self.assertRaises(ValueError) as cm_err:
        runner.run()
      self.assertIn("Blink-AI Benchmark did not finish successfully",
                    str(cm_err.exception))
    cm.assert_called_once()

    for browser in active_browsers:
      self.assertListEqual(browser.expected_js, [])

  def test_run_multimodal(self):
    stories = self.story_cls.from_names(
        ["multimodal_image", "multimodal_audio"])
    benchmark = self.benchmark_cls(stories)

    probe_results = {
        "multimodal_image": {
            "downloadTimeMs": 100.0,
            "sessionCreationTimeMs": 50.0,
            "coldTimeToFirstTokenMs": 10.0,
            "coldTotalPromptTimeMs": 100.0,
            "coldChunksPerSecond": 10.0,
            "warmTimeToFirstTokenMs": [2.0],
            "warmTotalPromptTimeMs": [20.0],
            "warmChunksPerSecond": [50.0]
        },
        "multimodal_audio": {
            "downloadTimeMs": 200.0,
            "sessionCreationTimeMs": 60.0,
            "coldTimeToFirstTokenMs": 15.0,
            "coldTotalPromptTimeMs": 120.0,
            "coldChunksPerSecond": 8.0,
            "warmTimeToFirstTokenMs": [3.0],
            "warmTotalPromptTimeMs": [25.0],
            "warmChunksPerSecond": [40.0]
        }
    }

    mock_metrics = copy.deepcopy(probe_results)
    mock_metrics.update(probe_results["multimodal_image"])

    repetitions = 1
    for _ in range(repetitions):
      for browser in self.browsers:
        self._setup_run_js_expect(browser, mock_metrics)

    for browser in self.browsers:
      browser.expected_js = copy.deepcopy(browser.expected_js)

    runner = Runner(
        self.out_dir,
        self.browsers,
        benchmark,
        env_config=EnvConfig(),
        env_validation_mode=ValidationMode.SKIP,
        platform=self.platform,
        repetitions=repetitions,
        throw=True,
        in_memory_result_db=True)

    with mock.patch.object(self.benchmark_cls, "validate_url") as cm:
      runner.run()
    cm.assert_called_once()

    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertEqual(len(urls), repetitions)
      self.assertIn(
          self.story_cls.URL + "?stories=multimodal_image%2Cmultimodal_audio",
          urls)
      self.assertListEqual(browser.expected_js, [])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
