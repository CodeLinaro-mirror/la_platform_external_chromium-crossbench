# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import unittest

from tests import test_helper

RUN_SNIPPET = """
if __name__ == "__main__":
  test_helper.run_pytest(__file__)
""".strip()
UNITTEST_DIR = pathlib.Path(__file__).parent


class MetaTestCase(unittest.TestCase):

  def test_unittest_runner_snippet(self):
    # - All unittests files must end with the snippet for the CQ to pick it up.
    # - pytest files (in end2end) use a different approach that doesn't rely
    #   on a per-file runner
    for test_file in UNITTEST_DIR.glob("**/test_*.py"):
      with self.subTest(test_file=test_file):
        self.assertTrue(
            test_file.read_text().rstrip().endswith(RUN_SNIPPET),
            f"{test_file} misses runner snippet: "
            "test_helper.run_pytest(__file__)")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
