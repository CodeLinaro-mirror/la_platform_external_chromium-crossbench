# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from typing_extensions import override

from crossbench.benchmarks.jetstream.jetstream import JetStreamCSVFormatter
from crossbench.benchmarks.jetstream.jetstream_2_0 import (
    JetStream20Benchmark, JetStream20Probe, JetStream20ProbeContext,
    JetStream20Story)
from crossbench.benchmarks.jetstream.jetstream_2_1 import (
    JetStream21Benchmark, JetStream21Probe, JetStream21ProbeContext,
    JetStream21Story)
from crossbench.benchmarks.jetstream.jetstream_2_2 import (
    JetStream22Benchmark, JetStream22Probe, JetStream22ProbeContext,
    JetStream22Story)
from crossbench.benchmarks.jetstream.jetstream_3_0 import (
    JetStream30Benchmark, JetStream30Probe, JetStream30ProbeContext,
    JetStream30Story)
from crossbench.probes.metric import MetricsMerger
from tests import test_helper
# Only import module to avoid exposing the abstract test classes to the runner.
from tests.crossbench.benchmarks import jetstream_helper


class JetStreamCSVFormatterTestCase(unittest.TestCase):

  def test_throw_missing_score(self):
    metrics = MetricsMerger({
        "Total/average": 10,
        "cdjs/average": 30,
        "cdjs/score": 40,
    })
    with self.assertRaisesRegex(KeyError, "Total/score"):
      _ = JetStreamCSVFormatter(metrics, lambda metric: metric.geomean).table

  def test_format_sorted(self):
    metrics = MetricsMerger({
        "Total/average": 10,
        "Total/score": 20,
        "cdjs/average": 30,
        "cdjs/score": 40,
    })
    table = JetStreamCSVFormatter(
        metrics, lambda metric: round(metric.geomean, 10)).table
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
    table = JetStreamCSVFormatter(
        metrics, lambda metric: round(metric.geomean, 10), sort=False).table
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
  @override
  def benchmark_cls(self):
    return JetStream20Benchmark

  @property
  @override
  def story_cls(self):
    return JetStream20Story

  @property
  @override
  def probe_cls(self):
    return JetStream20Probe

  @property
  @override
  def probe_context_cls(self):
    return JetStream20ProbeContext

  @property
  def name(self):
    return "jetstream_2.0"


class JetStream21TestCase(jetstream_helper.JetStream2BaseTestCase):

  @property
  @override
  def benchmark_cls(self):
    return JetStream21Benchmark

  @property
  @override
  def story_cls(self):
    return JetStream21Story

  @property
  @override
  def probe_cls(self):
    return JetStream21Probe

  @property
  @override
  def probe_context_cls(self):
    return JetStream21ProbeContext

  @property
  def name(self):
    return "jetstream_2.1"


class JetStream22TestCase(jetstream_helper.JetStream2BaseTestCase):

  @property
  @override
  def benchmark_cls(self):
    return JetStream22Benchmark

  @property
  @override
  def story_cls(self):
    return JetStream22Story

  @property
  @override
  def probe_cls(self):
    return JetStream22Probe

  @property
  @override
  def probe_context_cls(self):
    return JetStream22ProbeContext

  @property
  @override
  def name(self):
    return "jetstream_2.2"


class JetStream30TestCase(jetstream_helper.JetStream3BaseTestCase):

  @property
  @override
  def benchmark_cls(self):
    return JetStream30Benchmark

  @property
  @override
  def story_cls(self):
    return JetStream30Story

  @property
  @override
  def probe_cls(self):
    return JetStream30Probe

  @property
  @override
  def probe_context_cls(self):
    return JetStream30ProbeContext

  @property
  def name(self):
    return "jetstream_3.0"


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
