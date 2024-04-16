# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from crossbench.probes.all import GENERAL_PURPOSE_PROBES
from tests import test_helper


class GeneralPurposeProbeTestCase(unittest.TestCase):

  def general_purpose_probes(self):
    for probe_cls in GENERAL_PURPOSE_PROBES:
      with self.subTest(probe_cls=probe_cls):
        yield probe_cls

  def test_properties(self):
    for probe_cls in self.general_purpose_probes():
      self.assertTrue(probe_cls.IS_GENERAL_PURPOSE)
      self.assertTrue(probe_cls.NAME)

  def test_help(self):
    for probe_cls in self.general_purpose_probes():
      help_text = probe_cls.help_text()
      self.assertTrue(help)
      summary = probe_cls.summary_text()
      self.assertTrue(summary)
      self.assertIn(summary, help_text)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
