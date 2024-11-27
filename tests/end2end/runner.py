#!/usr/bin/env vpython3
# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# The --adb-device-id flag is required to run tests on your Android device.
# Otherwise, the Android tests will be ignored.

from __future__ import annotations

import argparse
import pathlib
import sys

import pytest

END2END_TEST_DIR = pathlib.Path(__file__).absolute().parent
REPO_DIR = pathlib.Path(__file__).absolute().parents[2]

if REPO_DIR not in sys.path:
  sys.path.insert(0, str(REPO_DIR))

if __name__ == "__main__":
  pass_through_args = sys.argv[1:]
  more_flags = []
  parser = argparse.ArgumentParser()
  parser.add_argument("--ignore-tests", required=False)
  parser.add_argument("--adb-device-id", required=False)
  parser.add_argument("--test-gsutil-path", required=False)
  args, _ = parser.parse_known_args()
  if args.ignore_tests:
    subfolders = args.ignore_tests.split(",")
    more_flags.extend([f"--ignore={END2END_TEST_DIR / x}" for x in subfolders])
  elif not args.adb_device_id:
    more_flags.append(f"--ignore={END2END_TEST_DIR / 'android'}")
  if args.test_gsutil_path:
    more_flags.append(f"--test-gsutil-path={args.test_gsutil_path}")
  return_code = pytest.main([
      "--verbose", "--dist=loadgroup", "--log-cli-level=DEBUG", "-o",
      "log_cli=True", "-rs",
      str(END2END_TEST_DIR), *pass_through_args
  ] + more_flags)
  sys.exit(return_code)
