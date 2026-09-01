# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing_extensions import override

from crossbench.benchmarks.speedometer.speedometer_1_0 import \
    Speedometer10Benchmark, Speedometer10Probe, Speedometer10ProbeContext, \
    Speedometer10Story
from tests import test_helper
from tests.crossbench.benchmarks.speedometer.helper import \
    Speedometer1BaseTestCase


class Speedometer10TestCase(Speedometer1BaseTestCase):

  @property
  @override
  def benchmark_cls(self):
    return Speedometer10Benchmark

  @property
  @override
  def story_cls(self):
    return Speedometer10Story

  @property
  @override
  def probe_cls(self):
    return Speedometer10Probe

  @property
  @override
  def probe_context_cls(self):
    return Speedometer10ProbeContext

  @property
  @override
  def name(self):
    return "speedometer_1.0"

  def test_default_all(self):
    default_story_names = [
        story.name for story in self.story_cls.default(separate=True)
    ]
    all_story_names = [
        story.name for story in self.story_cls.all(separate=True)
    ]
    self.assertListEqual(default_story_names, all_story_names)


# Don't expose abstract BaseTestCase to test runner
del Speedometer1BaseTestCase

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
