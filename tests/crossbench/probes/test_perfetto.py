# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import unittest

from crossbench.probes.all import PerfettoProbe
from tests import run_helper


class TestProbe(unittest.TestCase):

  def test_missing_config(self):
    with self.assertRaises(AssertionError):
      PerfettoProbe.from_config({})

  def test_parse_config(self):
    probe: PerfettoProbe = PerfettoProbe.from_config({"textproto": "TEXTPROTO"})
    self.assertEqual("TEXTPROTO", probe.textproto)
    self.assertEqual("perfetto", probe.perfetto_bin)


if __name__ == "__main__":
  run_helper.run_pytest(__file__)
