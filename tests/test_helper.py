# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import sys
from typing import Union

from crossbench import config

import pytest


is_google_env = config.is_google_env
root_dir = config.root_dir
config_dir = config.config_dir


def crossbench_dir() -> pathlib.Path:
  if is_google_env():
    return root_dir()
  return root_dir() / "crossbench"


def run_pytest(path: Union[str, pathlib.Path], *args):
  extra_args = [*args, *sys.argv[1:]]
  # Run tests single-threaded by default when running the test file directly.
  if "-n" not in extra_args:
    extra_args.extend(["-n", "1"])
  if "-r" not in extra_args:
    extra_args.extend(["-r", "s"])
  sys.exit(pytest.main([str(path), *extra_args]))
