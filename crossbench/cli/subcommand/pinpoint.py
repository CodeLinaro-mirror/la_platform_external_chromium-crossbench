# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench.cli.parser import CrossBenchArgumentParser
from crossbench.cli.subcommand.base import CrossbenchSubcommand
from crossbench.parse import NumberParser
from crossbench.pinpoint import pinpoint
from crossbench.pinpoint.user import UserEnum, list_user

if TYPE_CHECKING:
  import argparse


class PinpointSubcommand(CrossbenchSubcommand):
  """A subcommand for interacting with the Pinpoint service."""

  @override
  def add_cli_parser(self) -> argparse.ArgumentParser:
    pinpoint_parser = self.cli.subparsers.add_parser(
        "pinpoint", aliases=("pp",), help="Interact with the Pinpoint service.")
    assert isinstance(pinpoint_parser, CrossBenchArgumentParser)
    pinpoint_parser.add_argument(
        "action",
        choices=["list"],
        help="Displays all pinpoint jobs on the first page.")
    pinpoint_parser.add_argument(
        "-u",
        "--user",
        type=list_user,
        default=UserEnum.ME,
        help="User to filter jobs by. Can be 'me' (default), 'all', or an email address."
    )
    pinpoint_parser.add_argument(
        "-n",
        "--number",
        type=NumberParser.positive_int,
        default=20,
        help="Number of jobs to display.")
    pinpoint_parser.add_argument(
        "-t",
        "--truncate",
        type=NumberParser.positive_int,
        default=None,
        help="Truncate cell content to the specified maximum length.")
    return pinpoint_parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    pinpoint.run(args)
