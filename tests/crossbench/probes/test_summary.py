# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from unittest import mock

from crossbench import path as pth
from crossbench.probes.internal.summary import ResultsSummaryProbe
from crossbench.probes.results import ProbeResultDict
from tests import test_helper


class ResultsSummaryProbeTestCase(unittest.TestCase):

  def test_merge_missing(self):
    group = mock.Mock()
    group.first_run.results = ProbeResultDict(pth.AnyPath("test/out/results"))
    probe = ResultsSummaryProbe()
    result = probe.merge_cache_temperatures(group)
    self.assertTrue(result.is_empty)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
