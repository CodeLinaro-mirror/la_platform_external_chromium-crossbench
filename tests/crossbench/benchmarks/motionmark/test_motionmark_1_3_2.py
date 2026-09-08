# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing_extensions import override

from crossbench.benchmarks.motionmark.motionmark_1_3_2 import \
    MotionMark132Benchmark, MotionMark132Probe, MotionMark132ProbeContext, \
    MotionMark132Story
from tests import test_helper
from tests.crossbench.benchmarks.motionmark.helper import \
    MotionMark1BaseTestCase


class MotionMark132TestCase(MotionMark1BaseTestCase):

  @property
  @override
  def benchmark_cls(self):
    return MotionMark132Benchmark

  @property
  @override
  def story_cls(self):
    return MotionMark132Story

  @property
  @override
  def probe_cls(self):
    return MotionMark132Probe

  @property
  @override
  def probe_context_cls(self):
    return MotionMark132ProbeContext


del MotionMark1BaseTestCase

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
