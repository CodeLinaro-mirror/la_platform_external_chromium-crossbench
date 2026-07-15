# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from crossbench.probes.probe import Probe
from tests import test_helper
from tests.crossbench.runner.helper import BaseRunnerTestCase

if TYPE_CHECKING:
  from crossbench.runner.runner import Runner

from crossbench.benchmarks.benchmark_probe import BenchmarkProbeMixin
from tests.crossbench.mock_helper import MockBenchmark
from tests.crossbench.runner.mocks import MockProbe


class MockProbeWithName(Probe):

  def __init__(self, name: str = "additional_probe"):
    self._name = name
    super().__init__()

  @property
  def name(self) -> str:
    return self._name


class MockProbeWithAdditional(MockProbeWithName):

  def __init__(self, additional_probe: Probe, name: str):
    super().__init__(name)
    self.additional_probe = additional_probe

  def get_extra_probes(self, runner: Runner) -> Iterable[Probe]:
    del runner
    return [self.additional_probe]


class TestRunnerProbes(BaseRunnerTestCase):

  def test_auto_add_probe(self):
    additional_probe = MockProbeWithName()
    main_probe = MockProbeWithAdditional(additional_probe, "main_probe")

    runner = self.default_runner(probes=[main_probe])

    self.assertIn(main_probe, runner.probes)
    self.assertIn(additional_probe, runner.probes)
    self.assertTrue(runner.has_probe(main_probe.name))
    self.assertTrue(runner.has_probe(additional_probe.name))

  def test_auto_add_probe_recursive(self):
    additional_probe_2 = MockProbeWithName("additional_probe_2")
    additional_probe_1 = MockProbeWithAdditional(additional_probe_2,
                                                 "additional_probe_1")
    main_probe = MockProbeWithAdditional(additional_probe_1, "main_probe")

    runner = self.default_runner(probes=[main_probe])

    self.assertIn(main_probe, runner.probes)
    self.assertIn(additional_probe_1, runner.probes)
    self.assertIn(additional_probe_2, runner.probes)

  def test_auto_add_probe_deduplicate(self):
    additional_probe = MockProbeWithName()
    probe_1 = MockProbeWithAdditional(additional_probe, "probe_1")
    probe_2 = MockProbeWithAdditional(additional_probe, "probe_2")

    with self.assertRaisesRegex(ValueError, additional_probe.name):
      self.default_runner(probes=[probe_1, probe_2])

  # Tests that secondary "extra" probes attached automatically by a primary
  # probe are skipped if explicitly disabled via --no-probe.
  def test_no_probes_skips_extra_probe(self):
    additional_probe = MockProbeWithName("additional_probe")
    main_probe = MockProbeWithAdditional(additional_probe, "main_probe")

    runner = self.default_runner(
        probes=[main_probe], disabled_probes=["additional_probe"])

    self.assertIn(main_probe, runner.probes)
    self.assertNotIn(additional_probe, runner.probes)
    self.assertTrue(runner.has_probe(main_probe.name))
    self.assertFalse(runner.has_probe(additional_probe.name))

  # Tests that default probes automatically attached by a benchmark are
  # skipped if explicitly disabled via --no-probe.
  def test_no_probes_skips_benchmark_probe(self):

    class DummyBenchmarkProbe(BenchmarkProbeMixin, MockProbe):
      NAME = "benchmark_probe"

      def __init__(self, **kwargs):
        super().__init__("benchmark_probe", **kwargs)

    class BenchmarkWithProbe(MockBenchmark):
      PROBES = (DummyBenchmarkProbe,)

      def __init__(self, stories):
        super().__init__(stories)

    benchmark = BenchmarkWithProbe(self.stories)
    runner = self.default_runner(
        benchmark=benchmark, disabled_probes=["benchmark_probe"])

    self.assertFalse(runner.has_probe("benchmark_probe"))


del BaseRunnerTestCase

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
