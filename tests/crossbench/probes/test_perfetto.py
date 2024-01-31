# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from crossbench.cli.config.probe import ProbeConfig, ProbeListConfig

from crossbench.probes.all import PerfettoProbe
from tests import test_helper


class TestProbe(unittest.TestCase):

  def test_missing_config(self):
    with self.assertRaises(ValueError) as cm:
      PerfettoProbe.from_config({})
    self.assertIn("config", str(cm.exception))

  def test_parse_config(self):
    probe: PerfettoProbe = PerfettoProbe.from_config({"textproto": "TEXTPROTO"})
    self.assertEqual("TEXTPROTO", probe.textproto)
    self.assertEqual("perfetto", probe.perfetto_bin)

  def test_parse_example_config(self):
    config_file = (
        test_helper.config_dir() / "probe" /
        "perfetto.probe.config.example.hjson")
    self.assertTrue(config_file.is_file())
    probes = ProbeListConfig.load_path(config_file).probes
    self.assertEqual(len(probes), 1)
    probe = probes[0]
    self.assertIsInstance(probe, PerfettoProbe)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
