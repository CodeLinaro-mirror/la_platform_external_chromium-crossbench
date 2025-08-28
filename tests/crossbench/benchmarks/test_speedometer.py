# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from typing_extensions import override

from crossbench.benchmarks.speedometer.speedometer_2_0 import (
    Speedometer20Benchmark, Speedometer20Probe, Speedometer20ProbeContext,
    Speedometer20Story)
from crossbench.benchmarks.speedometer.speedometer_2_1 import (
    Speedometer21Benchmark, Speedometer21Probe, Speedometer21ProbeContext,
    Speedometer21Story)
from crossbench.benchmarks.speedometer.speedometer_3 import MeasurementMethod
from crossbench.benchmarks.speedometer.speedometer_3_0 import (
    Speedometer30Benchmark, Speedometer30Probe, Speedometer30ProbeContext,
    Speedometer30Story)
from crossbench.benchmarks.speedometer.speedometer_3_1 import (
    Speedometer31Benchmark, Speedometer31Probe, Speedometer31ProbeContext,
    Speedometer31Story)
from crossbench.benchmarks.speedometer.speedometer_main import (
    SpeedometerMainBenchmark, SpeedometerMainProbe,
    SpeedometerMainProbeContext, SpeedometerMainStory)
from crossbench.browsers.viewport import Viewport
from tests import test_helper
from tests.crossbench.benchmarks.speedometer_helper import (
    Speedometer2BaseTestCase, SpeedometerBaseTestCase)

if TYPE_CHECKING:
  from crossbench.types import Json
  from tests.crossbench.mock_browser import MockBrowser

class Speedometer20TestCase(Speedometer2BaseTestCase):

  @property
  @override
  def benchmark_cls(self):
    return Speedometer20Benchmark

  @property
  @override
  def story_cls(self):
    return Speedometer20Story

  @property
  @override
  def probe_cls(self):
    return Speedometer20Probe

  @property
  @override
  def probe_context_cls(self):
    return Speedometer20ProbeContext

  @property
  @override
  def name(self):
    return "speedometer_2.0"

  def test_default_all(self):
    default_story_names = [
        story.name for story in self.story_cls.default(separate=True)
    ]
    all_story_names = [
        story.name for story in self.story_cls.all(separate=True)
    ]
    self.assertListEqual(default_story_names, all_story_names)


class Speedometer21TestCase(Speedometer2BaseTestCase):

  @property
  @override
  def benchmark_cls(self):
    return Speedometer21Benchmark

  @property
  @override
  def story_cls(self):
    return Speedometer21Story

  @property
  @override
  def probe_cls(self):
    return Speedometer21Probe

  @property
  @override
  def probe_context_cls(self):
    return Speedometer21ProbeContext

  @property
  @override
  def name(self):
    return "speedometer_2.1"


class Speedometer3BaseTestCase(SpeedometerBaseTestCase):

  @property
  def name_all(self):
    return "all"

  def _setup_run_js_expect(self, browser: MockBrowser,
                           speedometer_probe_results: Json) -> None:
    # Page is ready
    browser.expect_js(result=True)
    # _setup_benchmark_client
    browser.expect_js()
    # _run_stories
    browser.expect_js()
    # Wait until done
    browser.expect_js(result=True)
    browser.expect_js(result=json.dumps(speedometer_probe_results))

  @dataclass
  class Namespace(SpeedometerBaseTestCase.Namespace):
    sync_wait = dt.timedelta(0)
    sync_warmup = dt.timedelta(0)
    measurement_method = MeasurementMethod.RAF
    story_viewport = None
    shuffle_seed = None
    detailed_metrics = False
    measure_prepare = None

  EXAMPLE_STORY_DATA: dict[str, Any] = {}

  def _generate_s3_metrics(self, name, values):
    return {
        "children": [],
        "delta": 0,
        "geomean": 39.20000000298023,
        "max": 39.20000000298023,
        "mean": 39.20000000298023,
        "min": 39.20000000298023,
        "name": name,
        "percentDelta": 0,
        "sum": 39.20000000298023,
        "unit": "ms",
        "values": values
    }

  @override
  def _generate_test_probe_results(self, iterations, story) -> Json:
    values = [21.3] * iterations
    probe_result = {}
    for substory_name in story.substories:
      probe_result[substory_name] = self._generate_s3_metrics(
          substory_name, values)

    for iteration in range(iterations):
      key = f"Iteration-{iteration}-Total"
      probe_result[key] = self._generate_s3_metrics(key, values)

    probe_result.update({
        "Geomean": self._generate_s3_metrics("Geomean", values),
        "Score": self._generate_s3_metrics("Score", values),
    })
    return probe_result

  def test_run_combined(self):
    self._run_combined(["TodoMVC-JavaScript-ES5", "TodoMVC-Backbone"])

  def test_run_separate(self):
    self._run_separate(["TodoMVC-JavaScript-ES5", "TodoMVC-Backbone"])

  def test_s3_probe_results(self):
    story_names = ("TodoMVC-JavaScript-ES5", "TodoMVC-Backbone")
    self.browsers = [self.browsers[0]]
    runner = self._test_run(
        story_names=story_names, separate=False, repetitions=2)
    self.assertEqual(len(runner.runs), 2)
    run_1 = runner.runs[0]
    run_2 = runner.runs[1]
    probe_file = f"{self.probe_cls.NAME}.json"
    with (run_1.out_dir / probe_file).open() as f:
      data_1 = json.load(f)
    with (run_2.out_dir / probe_file).open() as f:
      data_2 = json.load(f)
    keys_1 = tuple(data_1.keys())
    keys_2 = tuple(data_2.keys())
    self.assertTupleEqual(keys_1, keys_2)
    # Make sure the aggregate metrics are at the end
    expected_keys = story_names + ("Iteration-0-Total", "Iteration-1-Total",
                                   "Geomean", "Score")
    self.assertTupleEqual(keys_1, expected_keys)

    with (runner.story_groups[0].path / probe_file).open() as f:
      stories_data = json.load(f)
    self.assertTupleEqual(tuple(stories_data.keys()), expected_keys)

  def test_measurement_method_kwargs(self):
    args = self.Namespace()
    args.stories = "default"
    benchmark = self.benchmark_cls.from_cli_args(args)
    (story,) = benchmark.stories
    assert isinstance(story, self.story_cls)
    self.assertEqual(story.name, self.name)
    self.assertDictEqual(story.url_params, {})

    args.measurement_method = MeasurementMethod.TIMER
    benchmark = self.benchmark_cls.from_cli_args(args)
    (story,) = benchmark.stories
    assert isinstance(story, self.story_cls)
    self.assertEqual(story.name, self.name)
    self.assertDictEqual(story.url_params, {"measurementMethod": "timer"})

  def test_all_stories_kwargs_url_params(self):
    args = self.Namespace()
    args.stories = "all"
    benchmark = self.benchmark_cls.from_cli_args(args)
    (story,) = benchmark.stories
    assert isinstance(story, self.story_cls)
    self.assertEqual(story.name, "all")
    self.assertDictEqual(story.url_params,
                         {"suites": ",".join(story.SUBSTORIES)})

  def test_single_story_kwargs(self):
    args = self.Namespace()
    args.stories = "TodoMVC-jQuery"
    benchmark = self.benchmark_cls.from_cli_args(args)
    (story,) = benchmark.stories
    assert isinstance(story, self.story_cls)
    self.assertEqual(story.name, "TodoMVC-jQuery")
    self.assertDictEqual(story.url_params, {"suites": "TodoMVC-jQuery"})

  def test_iterations_kwargs(self):
    args = self.Namespace()
    args.stories = "default"
    benchmark = self.benchmark_cls.from_cli_args(args)
    (story,) = benchmark.stories
    assert isinstance(story, self.story_cls)
    self.assertEqual(story.iterations, 10)
    self.assertDictEqual(story.url_params, {})

    args.iterations = 10
    benchmark = self.benchmark_cls.from_cli_args(args)
    (story,) = benchmark.stories
    assert isinstance(story, self.story_cls)
    self.assertEqual(story.iterations, 10)
    self.assertDictEqual(story.url_params, {})

    args.iterations = 123
    benchmark = self.benchmark_cls.from_cli_args(args)
    (story,) = benchmark.stories
    assert isinstance(story, self.story_cls)
    self.assertEqual(story.iterations, 123)
    self.assertDictEqual(story.url_params, {"iterationCount": "123"})

  def test_sync_wait_kwargs(self):
    args = self.Namespace()
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertDictEqual(story.url_params, {})

    args.sync_wait = dt.timedelta(seconds=123.4)
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertDictEqual(story.url_params, {"waitBeforeSync": "123400"})

  def test_sync_warmup_kwargs(self):
    args = self.Namespace()
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertFalse(story.url_params)

    args.sync_warmup = dt.timedelta(seconds=123.4)
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertDictEqual(story.url_params, {"warmupBeforeSync": "123400"})

  def test_viewport_kwargs(self):
    args = self.Namespace()
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertFalse(story.url_params)

    args.story_viewport = Viewport(999, 888)
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertDictEqual(story.url_params, {"viewport": "999x888"})

  def test_shuffle_seed_kwargs(self):
    args = self.Namespace()
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertFalse(story.url_params)

    args.shuffle_seed = 1234
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertDictEqual(story.url_params, {"shuffleSeed": "1234"})

  def test_run_default(self):
    runner = self._test_run(iterations=10)
    self._verify_results(runner)
    default_story_name = self.story_cls.SUBSTORIES[0]
    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertIn(f"{self.story_cls.URL}?suites={default_story_name}", urls)
      self.assertNotIn(
          f"{self.story_cls.URL_LOCAL}?suites={default_story_name}", urls)

  def test_run_warmups(self):
    runner = self._test_run(iterations=10, warmup_repetitions=1)
    self._verify_results(runner)
    default_story_name = self.story_cls.SUBSTORIES[0]
    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertIn(f"{self.story_cls.URL}?suites={default_story_name}", urls)
      self.assertNotIn(
          f"{self.story_cls.URL_LOCAL}?suites={default_story_name}", urls)

  def test_run_custom_url(self):
    custom_url = "http://test.example.com/speedometer"
    runner = self._test_run(custom_url=custom_url, iterations=10)
    default_story_name = self.story_cls.SUBSTORIES[0]
    self._verify_results(runner)
    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertIn(f"{custom_url}?suites={default_story_name}", urls)
      self.assertNotIn(f"{self.story_cls.URL}?suites={default_story_name}",
                       urls)
      self.assertNotIn(
          f"{self.story_cls.URL_LOCAL}?suites={default_story_name}", urls)

  def test_run_custom_iterations(self):
    runner = self._test_run(iterations=7)
    self._verify_results(runner)
    default_story_name = self.story_cls.SUBSTORIES[0]
    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertIn(
          f"{self.story_cls.URL}?iterationCount=7&suites={default_story_name}",
          urls)
      self.assertNotIn(self.story_cls.URL, urls)
      self.assertNotIn(
          f"{self.story_cls.URL_LOCAL}?iterationCount=7"
          f"&suites={default_story_name}", urls)
      self.assertNotIn(self.story_cls.URL_LOCAL, urls)


class Speedometer30TestCase(Speedometer3BaseTestCase):

  @property
  @override
  def benchmark_cls(self):
    return Speedometer30Benchmark

  @property
  @override
  def story_cls(self):
    return Speedometer30Story

  @property
  @override
  def probe_cls(self):
    return Speedometer30Probe

  @property
  @override
  def probe_context_cls(self):
    return Speedometer30ProbeContext

  @property
  @override
  def name(self):
    return "speedometer_3.0"


class Speedometer31TestCase(Speedometer3BaseTestCase):

  @property
  @override
  def benchmark_cls(self):
    return Speedometer31Benchmark

  @property
  @override
  def story_cls(self):
    return Speedometer31Story

  @property
  @override
  def probe_cls(self):
    return Speedometer31Probe

  @property
  @override
  def probe_context_cls(self):
    return Speedometer31ProbeContext

  @property
  @override
  def name(self):
    return "speedometer_3.1"


class SpeedometeMainTestCase(Speedometer3BaseTestCase):

  @property
  @override
  def benchmark_cls(self):
    return SpeedometerMainBenchmark

  @property
  @override
  def story_cls(self):
    return SpeedometerMainStory

  @property
  @override
  def probe_cls(self):
    return SpeedometerMainProbe

  @property
  @override
  def probe_context_cls(self):
    return SpeedometerMainProbeContext

  @property
  @override
  def name(self):
    return "speedometer_main"

#  Don't expose abstract BaseTestCase to test runner
del SpeedometerBaseTestCase
del Speedometer2BaseTestCase
del Speedometer3BaseTestCase


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
