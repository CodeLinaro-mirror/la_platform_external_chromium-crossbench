# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import unittest

from crossbench.probes.frequency import ExtremeFrequency, FrequencyProbe
from tests import test_helper


class FrequencyProbeTest(unittest.TestCase):

  def test_parse_invalid_map_value(self):
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "Invalid value"):
      FrequencyProbe.from_config({"cpus": {"cpu0": "invalid"}})

  def test_parse_conflicting_wildcard(self):
    with self.assertRaisesRegex(argparse.ArgumentTypeError,
                                "should be the only key"):
      FrequencyProbe.from_config({"cpus": {"*": "max", "cpu0": "min"}})

  def test_parse_valid_wildcard_config(self):
    probe = FrequencyProbe.from_config({"cpus": {"*": "max"}})

    self.assertEqual(len(probe.cpu_frequency_map), 1)
    self.assertEqual(probe.cpu_frequency_map["*"], ExtremeFrequency.MAX)

  def test_parse_valid_non_wildcard_config(self):
    probe = FrequencyProbe.from_config(
        {"cpus": {
            "cpu0": "1111",
            "cpu1": 2222,
            "cpu2": "min",
            "cpu3": "max"
        }})

    self.assertEqual(len(probe.cpu_frequency_map), 4)
    self.assertEqual(probe.cpu_frequency_map["cpu0"], 1111)
    self.assertEqual(probe.cpu_frequency_map["cpu1"], 2222)
    self.assertEqual(probe.cpu_frequency_map["cpu2"], ExtremeFrequency.MIN)
    self.assertEqual(probe.cpu_frequency_map["cpu3"], ExtremeFrequency.MAX)

  def test_parse_valid_empty_configs(self):
    probe1 = FrequencyProbe.from_config({})
    probe2 = FrequencyProbe.from_config({"cpus": {}})

    self.assertFalse(probe1.cpu_frequency_map)
    self.assertFalse(probe2.cpu_frequency_map)

  def test_key(self):
    key1 = FrequencyProbe.from_config({"cpus": {"cpu0": "1111",}}).key
    key2 = FrequencyProbe.from_config({"cpus": {"cpu0": "2222",}}).key

    self.assertIsNotNone(key1)
    self.assertIsNotNone(key2)
    self.assertNotEqual(key1, key2)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
