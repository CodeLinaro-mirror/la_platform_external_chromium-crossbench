# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest

from ordered_set import OrderedSet

from crossbench.benchmarks.jetstream.jetstream_2_0 import JetStream20Benchmark
from crossbench.benchmarks.jetstream.jetstream_2_1 import JetStream21Benchmark
from crossbench.benchmarks.jetstream.jetstream_2_2 import JetStream22Benchmark
from crossbench.benchmarks.jetstream.jetstream_3_0 import JetStream30Benchmark
from crossbench.benchmarks.loading.loading_benchmark import PageLoadBenchmark
from crossbench.benchmarks.loading.loadline_presets import (
    LoadLinePhoneBenchmark, LoadLineTabletBenchmark)
from crossbench.benchmarks.manual.manual_benchmark import ManualBenchmark
from crossbench.benchmarks.memory.memory_benchmark import MemoryBenchmark
from crossbench.benchmarks.motionmark.motionmark_1_0 import \
    MotionMark10Benchmark
from crossbench.benchmarks.motionmark.motionmark_1_1 import \
    MotionMark11Benchmark
from crossbench.benchmarks.motionmark.motionmark_1_2 import \
    MotionMark12Benchmark
from crossbench.benchmarks.motionmark.motionmark_1_3 import \
    MotionMark13Benchmark
from crossbench.benchmarks.speedometer.speedometer_2_0 import \
    Speedometer20Benchmark
from crossbench.benchmarks.speedometer.speedometer_2_1 import \
    Speedometer21Benchmark
from crossbench.benchmarks.speedometer.speedometer_3_0 import \
    Speedometer30Benchmark
from tests import test_helper

ALL = (
    JetStream20Benchmark,
    JetStream21Benchmark,
    JetStream22Benchmark,
    JetStream30Benchmark,
    LoadLinePhoneBenchmark,
    LoadLineTabletBenchmark,
    ManualBenchmark,
    MotionMark10Benchmark,
    MotionMark11Benchmark,
    MotionMark12Benchmark,
    MotionMark13Benchmark,
    PageLoadBenchmark,
    Speedometer20Benchmark,
    Speedometer21Benchmark,
    Speedometer30Benchmark,
    MemoryBenchmark,
)


class AllBenchmarksTestCase(unittest.TestCase):

  def test_unique_classes(self):
    self.assertTupleEqual(ALL, tuple(OrderedSet(ALL)))

  def test_aliases(self):
    seen_names = OrderedSet()
    seen_aliases = OrderedSet()
    for benchmark_cls in ALL:
      with self.subTest(benchmark_cls=benchmark_cls):
        self.assertNotIn(benchmark_cls.NAME, seen_names)
        seen_names.add(benchmark_cls.NAME)
        for alias in benchmark_cls.aliases():
          self.assertNotIn(alias, seen_aliases)
          seen_aliases.add(alias)

  def test_story_classes(self):
    seen_story_classes = OrderedSet()
    for benchmark_cls in ALL:
      if benchmark_cls is MemoryBenchmark:
        continue
      if issubclass(benchmark_cls,
                    PageLoadBenchmark) and (benchmark_cls
                                            is not PageLoadBenchmark):
        continue
      self.assertNotIn(benchmark_cls.DEFAULT_STORY_CLS, seen_story_classes)
      seen_story_classes.add(benchmark_cls.DEFAULT_STORY_CLS)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
