# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest

from crossbench.benchmarks.jetstream.jetstream import JetStreamCSVFormatter
from crossbench.probes.metric import MetricsMerger
from tests import test_helper

# Only import module to avoid exposing the abstract test classes to the runner.


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


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
