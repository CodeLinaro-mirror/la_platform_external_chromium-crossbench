# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from crossbench.benchmarks.jetstream.jetstream_2 import JetStream2CSVFormatter
from crossbench.benchmarks.jetstream.jetstream_2_0 import (JetStream20Benchmark,
                                                           JetStream20Probe,
                                                           JetStream20Story)
from crossbench.benchmarks.jetstream.jetstream_2_1 import (JetStream21Benchmark,
                                                           JetStream21Probe,
                                                           JetStream21Story)
from crossbench.benchmarks.jetstream.jetstream_2_2 import (JetStream22Benchmark,
                                                           JetStream22Probe,
                                                           JetStream22Story)
from crossbench.benchmarks.jetstream.jetstream_3_0 import (JetStream30Benchmark,
                                                           JetStream30Probe,
                                                           JetStream30Story)
from crossbench.probes.metric import CSVFormatter, MetricsMerger, geomean
from tests import test_helper
# Only import module to avoid exposing the abstract test classes to the runner.
from tests.crossbench.benchmarks import jetstream_helper


class JetStream2CSVFormatterTestCase(unittest.TestCase):

  def test_format_sorted(self):
    metrics = MetricsMerger({
        "Total/average": 10,
        "Total/score": 20,
        "cdjs/average": 30,
        "cdjs/score": 40,
    })
    table = JetStream2CSVFormatter(metrics, lambda metric: metric.geomean).table
    self.assertSequenceEqual(table, [
        ("Total/score", "Total", "score", 20.0),
        ("cdjs/score", "cdjs", "score", 40.0),
        ("Total/average", "Total", "average", 10.0),
        ("Total/score", "Total", "score", 20.0),
        ("cdjs/average", "cdjs", "average", 30.0),
        ("cdjs/score", "cdjs", "score", 40.0),
    ])

  def test_format_unsorted(self):
    metrics = MetricsMerger({
        "cdjs/average": 30,
        "cdjs/score": 40,
        "Total/average": 10,
        "Total/score": 20,
    })
    table = JetStream2CSVFormatter(
        metrics, lambda metric: metric.geomean, sort=False).table
    self.assertSequenceEqual(table, [
        ("Total/score", "Total", "score", 20.0),
        ("cdjs/score", "cdjs", "score", 40.0),
        ("cdjs/average", "cdjs", "average", 30.0),
        ("cdjs/score", "cdjs", "score", 40.0),
        ("Total/average", "Total", "average", 10.0),
        ("Total/score", "Total", "score", 20.0),
    ])


class JetStream20TestCase(jetstream_helper.JetStream2BaseTestCase):

  @property
  def benchmark_cls(self):
    return JetStream20Benchmark

  @property
  def story_cls(self):
    return JetStream20Story

  @property
  def probe_cls(self):
    return JetStream20Probe

  @property
  def name(self):
    return "jetstream_2.0"


class JetStream21TestCase(jetstream_helper.JetStream2BaseTestCase):

  @property
  def benchmark_cls(self):
    return JetStream21Benchmark

  @property
  def story_cls(self):
    return JetStream21Story

  @property
  def probe_cls(self):
    return JetStream21Probe

  @property
  def name(self):
    return "jetstream_2.1"


class JetStream22TestCase(jetstream_helper.JetStream2BaseTestCase):

  @property
  def benchmark_cls(self):
    return JetStream22Benchmark

  @property
  def story_cls(self):
    return JetStream22Story

  @property
  def probe_cls(self):
    return JetStream22Probe

  @property
  def name(self):
    return "jetstream_2.2"


class JetStream30TestCase(jetstream_helper.JetStream3BaseTestCase):

  @property
  def benchmark_cls(self):
    return JetStream30Benchmark

  @property
  def story_cls(self):
    return JetStream30Story

  @property
  def probe_cls(self):
    return JetStream30Probe

  @property
  def name(self):
    return "jetstream_3.0"


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
