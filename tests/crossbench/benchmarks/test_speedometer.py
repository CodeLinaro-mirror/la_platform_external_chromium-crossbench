# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from dataclasses import dataclass
import datetime as dt
from crossbench.browsers.viewport import Viewport

from tests import test_helper

from crossbench.benchmarks.speedometer import speedometer_2_0
from crossbench.benchmarks.speedometer import speedometer_2_1
from crossbench.benchmarks.speedometer import speedometer_3_0
from tests.crossbench.benchmarks import speedometer_helper


class Speedometer20TestCase(speedometer_helper.SpeedometerBaseTestCase):

  @property
  def benchmark_cls(self):
    return speedometer_2_0.Speedometer20Benchmark

  @property
  def story_cls(self):
    return speedometer_2_0.Speedometer20Story

  @property
  def probe_cls(self):
    return speedometer_2_0.Speedometer20Probe

  @property
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



class Speedometer21TestCase(speedometer_helper.SpeedometerBaseTestCase):

  @property
  def benchmark_cls(self):
    return speedometer_2_1.Speedometer21Benchmark

  @property
  def story_cls(self):
    return speedometer_2_1.Speedometer21Story

  @property
  def probe_cls(self):
    return speedometer_2_1.Speedometer21Probe

  @property
  def name(self):
    return "speedometer_2.1"


class Speedometer30TestCase(speedometer_helper.SpeedometerBaseTestCase):

  @property
  def benchmark_cls(self):
    return speedometer_3_0.Speedometer30Benchmark

  @property
  def story_cls(self):
    return speedometer_3_0.Speedometer30Story

  @property
  def probe_cls(self):
    return speedometer_3_0.Speedometer30Probe

  @property
  def name(self):
    return "speedometer_3.0"

  @property
  def name_all(self):
    return "speedometer_3.0_all"

  def test_run_combined(self):
    self._run_combined(["TodoMVC-JavaScript-ES5", "TodoMVC-Backbone"])

  def test_run_separate(self):
    self._run_separate(["TodoMVC-JavaScript-ES5", "TodoMVC-Backbone"])

  @dataclass
  class Namespace(speedometer_helper.SpeedometerBaseTestCase.Namespace):
    sync_wait = dt.timedelta(0)
    sync_warmup = dt.timedelta(0)
    measurement_method = speedometer_3_0.MeasurementMethod.RAF
    story_viewport = None
    shuffle_seed = None

  def test_measurement_method_kwargs(self):
    args = self.Namespace()
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertEqual(story.measurement_method,
                       speedometer_3_0.MeasurementMethod.RAF)

    args.measurement_method = speedometer_3_0.MeasurementMethod.TIMER
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertEqual(story.measurement_method,
                       speedometer_3_0.MeasurementMethod.TIMER)
      self.assertDictEqual(story.url_params, {"measurementMethod": "timer"})

  def test_sync_wait_kwargs(self):
    args = self.Namespace()
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertEqual(story.sync_wait, dt.timedelta(0))

    with self.assertRaises(argparse.ArgumentTypeError):
      args.sync_wait = dt.timedelta(seconds=-123.4)
      self.benchmark_cls.from_cli_args(args)

    args.sync_wait = dt.timedelta(seconds=123.4)
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertEqual(story.sync_wait, dt.timedelta(seconds=123.4))
      self.assertDictEqual(story.url_params, {"waitBeforeSync": "123400"})

  def test_sync_warmup_kwargs(self):
    args = self.Namespace()
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertEqual(story.sync_warmup, dt.timedelta(0))

    with self.assertRaises(argparse.ArgumentTypeError):
      args.sync_warmup = dt.timedelta(seconds=-123.4)
      self.benchmark_cls.from_cli_args(args)

    args.sync_warmup = dt.timedelta(seconds=123.4)
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertEqual(story.sync_warmup, dt.timedelta(seconds=123.4))
      self.assertDictEqual(story.url_params, {"warmupBeforeSync": "123400"})

  def test_viewport_kwargs(self):
    args = self.Namespace()
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertEqual(story.viewport, None)

    with self.assertRaises(argparse.ArgumentTypeError):
      args.story_viewport = Viewport.FULLSCREEN
      self.benchmark_cls.from_cli_args(args)

    args.story_viewport = Viewport(999, 888)
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertEqual(story.viewport, Viewport(999, 888))
      self.assertDictEqual(story.url_params, {"viewport": "999x888"})

  def test_shuffle_seed_kwargs(self):
    args = self.Namespace()
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertEqual(story.shuffle_seed, None)

    with self.assertRaises(argparse.ArgumentTypeError):
      args.shuffle_seed = "some invalid value"
      self.benchmark_cls.from_cli_args(args)

    args.shuffle_seed = 1234
    benchmark = self.benchmark_cls.from_cli_args(args)
    for story in benchmark.stories:
      assert isinstance(story, self.story_cls)
      self.assertEqual(story.shuffle_seed, 1234)
      self.assertDictEqual(story.url_params, {"shuffleSeed": "1234"})

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
