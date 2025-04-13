# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from crossbench.action_runner.default_action_runner import DefaultActionRunner
from crossbench.action_runner.default_bond_action_runner import (
    DefaultBondActionRunner)
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase


class DefaultBondActionRunnerTestCase(BaseCrossbenchTestCase):

  def test_get_current_conference_code(self):
    action_runner = DefaultActionRunner()
    bond_action_runner = DefaultBondActionRunner(action_runner)
    for browser in self.browsers:
      browser.set_current_url("https://meet.google.com/abc-def-ghi")
      code = bond_action_runner.get_current_conference_code(browser=browser)
      self.assertEqual(code, "abc-def-ghi")

  def test_get_current_conference_code_invalid(self):
    action_runner = DefaultActionRunner()
    bond_action_runner = DefaultBondActionRunner(action_runner)
    for browser in self.browsers:
      browser.set_current_url("https://www.google.com")
      with self.assertRaisesRegex(RuntimeError,
                                  "Unsupported URL for Bond action"):
        bond_action_runner.get_current_conference_code(browser=browser)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
