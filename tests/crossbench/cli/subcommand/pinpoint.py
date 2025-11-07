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

  @mock.patch("crossbench.cli.subcommand.pinpoint.print_bots")
  def test_pinpoint_bots_calls_print_bots(self, mock_print_bots):
    cli = CrossBenchCLI()
    cli.run(["pinpoint", "bots"])
    mock_print_bots.assert_called_once()


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
