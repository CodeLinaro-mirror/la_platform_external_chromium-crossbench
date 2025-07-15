# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import re
import unittest

from tests import test_helper

RUN_SNIPPET = """
if __name__ == "__main__":
  test_helper.run_pytest(__file__)
""".strip()
FUTURE_ANNOTATIONS_SNIPPET = "from __future__ import annotations"

COMMENTS_ONLY_RE = re.compile(r"^(?:#.*|\s*)*$", re.MULTILINE)

UNITTEST_DIR = pathlib.Path(__file__).parent
ROOT_DIR = UNITTEST_DIR.parents[1]
CROSSBENCH_DIR = ROOT_DIR / "crossbench"


class MetaTestCase(unittest.TestCase):

  def test_unittest_runner_snippet(self):
    # - All unittests files must end with the snippet for the CQ to pick it up.
    # - pytest files (in end2end) use a different approach that doesn't rely
    #   on a per-file runner
    for test_file in UNITTEST_DIR.glob("**/test_*.py"):
      with self.subTest(test_file=str(test_file)):
        self.assertTrue(
            test_file.read_text().rstrip().endswith(RUN_SNIPPET),
            f"{test_file} misses runner snippet: "
            "test_helper.run_pytest(__file__)")

  def test_future_annotation(self):
    for py_file in CROSSBENCH_DIR.glob("**/*.py"):
      with self.subTest(py_file=str(py_file)):
        text = py_file.read_text()
        if FUTURE_ANNOTATIONS_SNIPPET in text:
          continue
        if "pytype: skip-file" in text:
          continue
        if py_file.name == "__init__.py" and COMMENTS_ONLY_RE.fullmatch(text):
          continue
        self.fail(f"{py_file} is missing future annotation")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
