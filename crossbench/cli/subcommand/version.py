# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench import __version__
from crossbench.cli.subcommand.base import CrossbenchSubcommand

if TYPE_CHECKING:
  import argparse

  from crossbench.cli.parser import CBArgumentParser
  from crossbench.cli.types import Subparsers


class VersionSubcommand(CrossbenchSubcommand):

  @override
  def register_subcommand(self,
                          subparsers: Subparsers) -> argparse.ArgumentParser:
    self._parser = subparsers.add_parser(
        "version",
        help="Show program's version number and exit, same as --version")
    self._parser.set_defaults(crossbench_subcommand=self)
    return self.parser

  @override
  def add_cli_arguments(self, parser: CBArgumentParser) -> CBArgumentParser:
    return parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    print(f"{sys.argv[0]} {__version__}")
    sys.exit(0)
