#!/usr/bin/env python3
# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
import platform
import re

USE_PYTHON3 = True


def CheckChange(input_api, output_api, on_commit):
  tests = []
  results = []
  testing_env = dict(input_api.environ)
  testing_path = pathlib.Path(input_api.PresubmitLocalPath())
  crossbench_test_path = testing_path / "tests" / "crossbench"
  testing_env["PYTHONPATH"] = input_api.os_path.pathsep.join(
      map(str, [testing_path, crossbench_test_path]))
  # ---------------------------------------------------------------------------
  # Validate the vpython spec
  if platform.system() in ("Linux", "Darwin"):
    tests += input_api.canned_checks.CheckVPythonSpec(input_api, output_api)
  # ---------------------------------------------------------------------------
  # Pylint
  disabled_warnings = [
      "missing-module-docstring",
      "missing-class-docstring",
      "useless-super-delegation",
      "useless-return",
      "line-too-long",  # Annoying false-positives on URLs.
      "cyclic-import",  # TODO: This is not working as expected with pytype.
      "no-member",  # Need newer pylint to handle issues with generics.
      "bad-option-value"  # Some annotations are only supported in
      # newer pylint versions.
  ]
  if on_commit:
    files_to_check = [r"^[^\.]+\.py$"]
  else:
    # By default, the pylint canned check lints all Python files together to
    # check for potential problems between dependencies. This is slow to run
    # across all of crossbench (>2 min), so only lint affected files.
    files = [file.AbsoluteLocalPath() for file in input_api.AffectedFiles()]
    files_to_check = [
        re.escape(
            input_api.os_path.relpath(file_path,
                                      input_api.PresubmitLocalPath()))
        for file_path in files
        if input_api.fnmatch.fnmatch(file_path, "*.py")
    ]
  tests += input_api.canned_checks.GetPylint(
      input_api,
      output_api,
      files_to_check=files_to_check,
      # TODO: enable globally once all lint issues are fixed.
      # pylintrc=".pylintrc",
      disabled_warnings=disabled_warnings)
  # ---------------------------------------------------------------------------
  # License header checks
  results += input_api.canned_checks.CheckLicense(input_api, output_api)
  # ---------------------------------------------------------------------------
  # Only run test_cli to speed up the presubmit checks
  if on_commit:
    dirs_to_check = crossbench_test_path.glob("**")
    files_to_check = [r".*test_.*\.py$"]
  else:
    # Only check a small subset on upload
    dirs_to_check = [crossbench_test_path / "cli"]
    files_to_check = [r".*test_cli_fast_.*\.py$"]
  for dir_to_check in dirs_to_check:
    # Skip potentially empty dirs
    if dir_to_check.name == "__pycache__":
      continue
    # End-to-end tests require custom setup and are not suited for presubmits.
    if "end2end" in dir_to_check.parts:
      continue
    tests += input_api.canned_checks.GetUnitTestsInDirectory(
        input_api,
        output_api,
        directory=dir_to_check,
        env=testing_env,
        files_to_check=files_to_check,
        skip_shebang_check=True,
        run_on_python2=False)
  # ---------------------------------------------------------------------------
  # Run all test
  results += input_api.RunTests(tests)
  return results


def CheckChangeOnUpload(input_api, output_api):
  return CheckChange(input_api, output_api, on_commit=False)


def CheckChangeOnCommit(input_api, output_api):
  return CheckChange(input_api, output_api, on_commit=True)
