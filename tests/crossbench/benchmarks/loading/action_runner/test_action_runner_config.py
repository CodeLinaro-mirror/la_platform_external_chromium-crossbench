# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import unittest

from crossbench.benchmarks.loading.action_runner.android_input_action_runner import \
    AndroidInputActionRunner
from crossbench.benchmarks.loading.action_runner.basic_action_runner import \
    BasicActionRunner
from crossbench.benchmarks.loading.action_runner.chromeos_input_action_runner import \
    ChromeOSInputActionRunner
from crossbench.benchmarks.loading.action_runner.config import \
    ActionRunnerConfig
from tests import test_helper


class ActionRunnerConfigTest(unittest.TestCase):

  def test_parse_invalid(self):
    for invalid in ["bas", "adnroid", "chroms"]:
      with self.subTest(pattern=invalid):
        with self.assertRaises((argparse.ArgumentTypeError, ValueError)):
          ActionRunnerConfig.parse(invalid)

  def test_parse_basic(self):
    action_runner = ActionRunnerConfig.parse("basic")
    self.assertIsInstance(action_runner, BasicActionRunner)

  def test_parse_android(self):
    action_runner = ActionRunnerConfig.parse("android")
    self.assertIsInstance(action_runner, AndroidInputActionRunner)

  def test_parse_chromeos(self):
    action_runner = ActionRunnerConfig.parse("chromeos")
    self.assertIsInstance(action_runner, ChromeOSInputActionRunner)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
