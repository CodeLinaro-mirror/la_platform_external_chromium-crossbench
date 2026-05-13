# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench.cli.subcommand.base import CrossbenchSubcommand
from crossbench.cli.subcommand.devtools_recorder_proxy.default import \
    CrossbenchDevToolsRecorderProxy

if TYPE_CHECKING:
  import argparse

  from crossbench.cli.parser import CBArgumentParser
  from crossbench.cli.types import Subparsers

class DevtoolsRecorderProxySubcommand(CrossbenchSubcommand):

  @override
  def register_subcommand(self,
                          subparsers: Subparsers) -> argparse.ArgumentParser:
    self._parser = subparsers.add_parser(
        "devtools-recorder-proxy",
        aliases=["devtools"],
        help=("Starts a local server to communicate with the "
              "DevTools Recorder extension."))
    self._parser.set_defaults(crossbench_subcommand=self)
    return self.parser

  @override
  def add_cli_arguments(self, parser: CBArgumentParser) -> CBArgumentParser:
    parser.add_argument(
        "--disable-token-authentication",
        dest="use_auth_token",
        default=True,
        action="store_false",
        help=("Disable token-based authentication. "
              "Unsafe, only use for local development."))
    return parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    CrossbenchDevToolsRecorderProxy.run_subcommand(args)
