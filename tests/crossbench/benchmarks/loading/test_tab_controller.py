# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import unittest

from crossbench.benchmarks.loading.tab_controller import TabController
from tests import test_helper


class TabControllerTest(unittest.TestCase):

  def test_parse_invalid(self):
    for invalid in ["sing", "mult", "mlt", "5"]:
      with self.subTest(pattern=invalid):
        with self.assertRaises((argparse.ArgumentTypeError, ValueError)):
          TabController.parse(invalid)

  def test_parse_multiple(self):
    tab_controller = TabController.parse("multiple")
    self.assertTrue(tab_controller.multiple_tabs)

  def test_parse_single(self):
    tab_controller = TabController.parse("single")
    self.assertFalse(tab_controller.multiple_tabs)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
