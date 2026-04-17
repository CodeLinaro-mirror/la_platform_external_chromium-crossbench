#!/usr/bin/env vpython3
# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import sys
from typing import Final

import pytest

FILE_PATH: Final = pathlib.Path(__file__).absolute()
TEST_DIR: Final = FILE_PATH.absolute().parent
REPO_DIR: Final = FILE_PATH.absolute().parents[3]

if REPO_DIR not in sys.path:
  sys.path.insert(0, str(REPO_DIR))

from tests.test_helper import DEFAULT_PYTEST_FLAGS, DurationPlugin, to_flags \
    # noqa: E402

if __name__ == "__main__":
  pass_through_args = sys.argv[1:]
  return_code = pytest.main([
      *to_flags(DEFAULT_PYTEST_FLAGS),
      str(TEST_DIR),
      *pass_through_args,
  ],
                            plugins=[DurationPlugin()])

  # Retry failed tests once
  if return_code > 0:
    return_code = pytest.main([
        *to_flags(DEFAULT_PYTEST_FLAGS),
        "--last-failed",
        "--last-failed-no-failures=none",
        str(TEST_DIR),
        *pass_through_args,
    ],
                              plugins=[DurationPlugin()])

  sys.exit(return_code)
