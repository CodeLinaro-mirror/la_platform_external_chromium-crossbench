# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import Final
from unittest import mock

from crossbench.cli.cli import CrossBenchCLI
from crossbench.cli.subcommand.setup_wpr_ethernet import (
  SetupWprEthernetSubcommand,
)
from tests import test_helper
from tests.crossbench.base import BaseCliTestCase, SysExitTestException

_SETUP_NETWORK_PATCH_TARGET: Final[str] = (
  "crossbench.cli.subcommand.setup_wpr_ethernet.SetupNetwork"
)


class SetupWprEthernetSubcommandTest(BaseCliTestCase):
  def setUp(self) -> None:
    super().setUp()
    self.cli_instance = CrossBenchCLI()
    self.subcommand = self.cli_instance.subcommands["setup_wpr_ethernet"]
    self.assertIsInstance(self.subcommand, SetupWprEthernetSubcommand)

  def test_aliases_registered(self) -> None:
    self.assertIs(
      self.cli_instance.subcommands["setup-wpr-ethernet"], self.subcommand
    )
    self.assertNotIn(
      "setup_cross_platform_mode", self.cli_instance.subcommands
    )

  def test_missing_interface(self) -> None:
    with (
      mock.patch(_SETUP_NETWORK_PATCH_TARGET) as mock_setup,
      self.assertRaises(SysExitTestException),
    ):
      self.run_cli("setup_wpr_ethernet")
    mock_setup.assert_not_called()

  def test_run_primary_name(self) -> None:
    with mock.patch(_SETUP_NETWORK_PATCH_TARGET) as mock_setup:
      self.run_cli("setup_wpr_ethernet", "--interface=en7")
    mock_setup.assert_called_once_with("en7")
    mock_setup.return_value.run.assert_called_once()


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
