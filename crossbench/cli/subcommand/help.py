# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench.cli.subcommand.base import CrossbenchSubcommand
from crossbench.cli.subcommand.describe import DescribeSubcommand

if TYPE_CHECKING:
  import argparse

  from crossbench.cli.parser import CBArgumentParser
  from crossbench.cli.types import Subparsers


class HelpSubcommand(CrossbenchSubcommand):

  @override
  def register_subcommand(self,
                          subparsers: Subparsers) -> argparse.ArgumentParser:
    # Just for completeness we want to support "--help" and "help"
    self._parser = subparsers.add_parser(
        "help",
        help=("Print the top-level by default, same as --help. "
              "Use `help $PROBE`, or `help $BENCHMARK` to print more details."))
    self._parser.set_defaults(crossbench_subcommand=self)
    return self.parser

  @override
  def add_cli_arguments(self, parser: CBArgumentParser) -> CBArgumentParser:
    help_parser = parser
    help_parser.add_argument(
        "search_terms",
        nargs="*",
        help="Use a benchmark, probe or network name to display more details.")
    return help_parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    if args.search_terms:
      subcommand = self.cli.subcommands["describe"]
      assert isinstance(subcommand, DescribeSubcommand)
      subcommand.run_from_help(args)
    else:
      self.cli.parser.print_help()
    sys.exit(0)
