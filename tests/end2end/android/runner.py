#!/usr/bin/env vpython3
# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import sys

import pytest

FILE_PATH = pathlib.Path(__file__).absolute()
TEST_DIR = FILE_PATH.absolute().parent
REPO_DIR = FILE_PATH.absolute().parents[3]

if REPO_DIR not in sys.path:
  sys.path.insert(0, str(REPO_DIR))

if __name__ == "__main__":
  pass_through_args = sys.argv[1:]
  return_code = pytest.main([
      "--verbose", "--dist=no", "--numprocesses=1", "--log-cli-level=DEBUG",
      "-o", "log_cli=True", "-rs",
      str(TEST_DIR), *pass_through_args
  ])
  sys.exit(return_code)
