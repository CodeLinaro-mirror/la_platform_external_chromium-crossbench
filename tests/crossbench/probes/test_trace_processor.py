# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

import hjson

from crossbench import plt
from crossbench.cli.config.probe import ProbeListConfig
from crossbench.probes.all import TraceProcessorProbe
from tests import test_helper


class TraceProcessorProbeTestCase(unittest.TestCase):

  def test_missing_probes(self):
    with self.assertRaises(ValueError) as cm:
      TraceProcessorProbe.from_config({})
    self.assertIn("probes", str(cm.exception))

  @unittest.skipIf(hjson.__name__ != "hjson", "hjson not available")
  @unittest.skipIf(not plt.PLATFORM.which("trace_processor"),
                   "trace_processor not available")
  def test_parse_config(self):
    probe: TraceProcessorProbe = TraceProcessorProbe.from_config(
        {"probes": ["probe1", "probe2"]})
    self.assertEqual(["probe1", "probe2"], probe.probes)

  @unittest.skipIf(hjson.__name__ != "hjson", "hjson not available")
  @unittest.skipIf(not plt.PLATFORM.which("trace_processor"),
                   "trace_processor not available")
  def test_parse_example_config(self):
    config_file = (
        test_helper.config_dir() / "doc/probe/trace_processor.config.hjson")
    self.assertTrue(config_file.is_file())
    probes = ProbeListConfig.load_path(config_file).probes
    self.assertEqual(len(probes), 2)
    probe = probes[0]
    self.assertIsInstance(probe, TraceProcessorProbe)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
