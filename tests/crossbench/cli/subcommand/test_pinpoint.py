# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest
from unittest import mock

from crossbench.cli.cli import CrossBenchCLI
from tests import test_helper


class PinpointSubcommandTest(unittest.TestCase):
  """Verifies that subcommands call the right functions."""

  def setUp(self):
    super().setUp()
    self.cli = CrossBenchCLI()
    self.patcher_print = mock.patch("builtins.print")
    self.mock_print = self.patcher_print.start()

  def tearDown(self):
    super().tearDown()
    self.patcher_print.stop()

  @mock.patch("crossbench.cli.subcommand.pinpoint.fetch_bots")
  def test_pinpoint_bots_prints_filtered_bots(self, mock_fetch_bots):
    mock_fetch_bots.return_value = [
        "linux-r350-perf", "win-10-perf", "win-11-perf"
    ]
    self.cli.run(["pinpoint", "bots", "--filter", "win"])
    self.mock_print.assert_called_once_with("win-10-perf\nwin-11-perf")

  @mock.patch("crossbench.cli.subcommand.pinpoint.fetch_benchmarks")
  def test_pinpoint_benchmarks_prints_filtered_benchmarks(
      self, mock_fetch_benchmarks):
    mock_fetch_benchmarks.return_value = [
        "speedometer2", "speedometer3", "jetstream2"
    ]
    self.cli.run(["pinpoint", "benchmarks", "--filter", "speedometer"])
    self.mock_print.assert_called_once_with("speedometer2\nspeedometer3")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
