# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse

from typing_extensions import override

from crossbench.benchmarks.speedometer.speedometer_3_0 import \
    Speedometer30Benchmark, Speedometer30Probe, Speedometer30ProbeContext, \
    Speedometer30Story
from tests import test_helper
from tests.crossbench.benchmarks.speedometer.helper import \
    Speedometer3BaseTestCase


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

  def test_cli_measure_prepare_not_supported(self):
    parser = self.create_parser()
    with self.assertRaises((argparse.ArgumentError, SystemExit)):
      parser.parse_args(["--measure-prepare"])


#  Don't expose abstract BaseTestCase to test runner
del Speedometer3BaseTestCase

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
