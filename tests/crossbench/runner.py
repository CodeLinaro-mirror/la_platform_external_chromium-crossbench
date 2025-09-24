#!/usr/bin/env vpython3
# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import sys

import pytest

FILE_PATH = pathlib.Path(__file__).absolute()
TEST_DIR = FILE_PATH.parent
REPO_DIR = FILE_PATH.parents[2]

if REPO_DIR not in sys.path:
  sys.path.insert(0, str(REPO_DIR))

from tests.test_helper import DEFAULT_PYTEST_FLAGS, to_flags  # noqa: E402

if __name__ == "__main__":
  pass_through_args = sys.argv[1:]
  flags = dict(DEFAULT_PYTEST_FLAGS)
  flags["--numprocesses"] = "auto"
  return_code = pytest.main([
      *to_flags(flags),
      str(TEST_DIR),
      *pass_through_args,
  ])
  sys.exit(return_code)
