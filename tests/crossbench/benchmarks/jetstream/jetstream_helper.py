# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import abc
import argparse
import copy
import csv
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Type
from unittest import mock

from typing_extensions import override

from crossbench.env.runner_env import EnvConfig, RunnerEnv, ValidationMode
from crossbench.runner.runner import Runner
from tests.crossbench.benchmarks import helper

if TYPE_CHECKING:
  from crossbench.action_runner.config import ActionRunnerConfig
  from crossbench.benchmarks.jetstream.jetstream_2 import \
      JetStream2Benchmark, JetStream2Probe, JetStream2ProbeContext, \
      JetStream2Story


class JetStream2BaseTestCase(
    helper.PressBaseBenchmarkTestCase, metaclass=abc.ABCMeta):

  @property
  @abc.abstractmethod
  @override
  def benchmark_cls(self) -> Type[JetStream2Benchmark]:
    pass

  @property
  @abc.abstractmethod
  @override
  def story_cls(self) -> Type[JetStream2Story]:
    pass

  @property
  @abc.abstractmethod
  def probe_cls(self) -> Type[JetStream2Probe]:
    pass

  @property
  @abc.abstractmethod
  def probe_context_cls(self) -> Type[JetStream2ProbeContext]:
    pass

  def test_run_throw(self):
    self._test_run(throw=True)

  def test_run_default(self):
    self._test_run()
    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertIn(self.story_cls.URL, urls)
      self.assertNotIn(self.story_cls.URL_LOCAL, urls)

  def test_run_custom_url(self):
    custom_url = "http://test.example.com/jetstream"
    self._test_run(custom_url)
    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertIn(custom_url, urls)
      self.assertNotIn(self.story_cls.URL, urls)
      self.assertNotIn(self.story_cls.URL_LOCAL, urls)

  def _test_run(self, custom_url: Optional[str] = None, throw: bool = False):
    repetitions = 3
    stories = self.story_cls.from_names(["WSL"], url=custom_url)
    example_story_data = {
        "firstIteration": 1,
        "average": 0.1,
        "worst4": 1.1,
        "score": 1
    }
    # The order should match Runner.get_runs
    for _ in range(repetitions):
      for _ in stories:
        jetstream_probe_results = {
            story.name: example_story_data for story in stories
        }
        for browser in self.browsers:
          # Ready state complete
          browser.expect_js(result=True)
          # Page is ready
          browser.expect_js(result=True)
          # filter benchmarks
          browser.expect_js()
          # UI is updated and ready,
          browser.expect_js(result=True)
          # Start running benchmark
          browser.expect_js()
          # Wait until done
          browser.expect_js(result=True)
          browser.expect_js(result=json.dumps(jetstream_probe_results))
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
    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertEqual(len(urls), repetitions)
      self.assertTrue(browser.was_js_invoked(self.probe_context_cls.JS))

    csv_file = self.out_dir / f"{self.probe_cls.NAME}.csv"
    with csv_file.open(encoding="utf-8") as f:
      csv_data = list(csv.DictReader(f, delimiter="\t"))
    self.assertListEqual(
        list(csv_data[0].keys()), ["label", "", "dev", "stable"])
    self.assertDictEqual(
        csv_data[1],
        {
            "label": "version",
            "dev": "102.22.33.44",
            "stable": "100.22.33.44",
            # One padding element
            "": ""
        })

    with self.assertLogs(level="INFO") as cm:
      for probe in runner.probes:
        for run in runner.runs:
          probe.log_run_result(run)
    output = "\n".join(cm.output)
    self.assertIn("JetStream results", output)

    with self.assertLogs(level="INFO") as cm:
      for probe in runner.probes:
        probe.log_browsers_result(runner.browser_group)
    output = "\n".join(cm.output)
    self.assertIn("JetStream results", output)
    self.assertIn("102.22.33.44", output)
    self.assertIn("100.22.33.44", output)

  @dataclass
  class Namespace(argparse.Namespace):
    stories = "default"
    iterations: int | None = None
    separate: bool = False
    custom_benchmark_url: str | None = None
    detailed_metrics: bool = False
    action_runner_config: ActionRunnerConfig | None = None

  def test_iterations_kwargs(self):
    args = self.Namespace()
    args.stories = "default"
    benchmark = self.benchmark_cls.from_cli_args(args)
    (story,) = benchmark.stories
    assert isinstance(story, self.story_cls)
    self.assertIsNone(story.iterations)
    self.assertDictEqual(story.url_params, {})

    args.iterations = 10
    benchmark = self.benchmark_cls.from_cli_args(args)
    (story,) = benchmark.stories
    assert isinstance(story, self.story_cls)
    self.assertEqual(story.iterations, 10)
    self.assertDictEqual(story.url_params, {"iterationCount": "10"})

    args.iterations = 123
    benchmark = self.benchmark_cls.from_cli_args(args)
    (story,) = benchmark.stories
    assert isinstance(story, self.story_cls)
    self.assertEqual(story.iterations, 123)
    self.assertDictEqual(story.url_params, {"iterationCount": "123"})


# TODO: introduce JetStreamBaseTestCase
class JetStream3BaseTestCase(JetStream2BaseTestCase, metaclass=abc.ABCMeta):
  pass
