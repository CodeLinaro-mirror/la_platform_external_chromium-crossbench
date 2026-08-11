# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench.cli.subcommand.base import CrossbenchSubcommand
from crossbench.parse import PathParser
from crossbench.uploader import results_uploader

if TYPE_CHECKING:
  import argparse

  from crossbench.cli.parser import CBArgumentParser
  from crossbench.cli.types import Subparsers


class UploadResultsSubcommand(CrossbenchSubcommand):
  """A subcommand for uploading previously collected benchmark results."""

  @override
  def register_subcommand(self,
                          subparsers: Subparsers) -> argparse.ArgumentParser:
    self._parser = subparsers.add_parser(
        "upload-results",
        aliases=(
            "upload_results",
            "upload-result",
            "upload_result",
        ),
        help=("Uploads previously collected benchmark results to a remote "
              "location."))
    self._parser.set_defaults(crossbench_subcommand=self)
    return self.parser

  @override
  def add_cli_arguments(self, parser: CBArgumentParser) -> CBArgumentParser:
    parser.add_argument(
        "result_dir",
        type=PathParser.dir_path,
        help="Path to the benchmark result directory.")
    parser.add_argument(
        "target_url",
        type=results_uploader.target_url,
        help=("Target upload URL. "
              "Currently, only Google Cloud Storage is supported."))
    self.cli.add_debugging_arguments(parser)
    return parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    url = results_uploader.upload(
        source=args.result_dir, target=args.target_url)
    if not url:
      logging.error("Upload failed.")
      sys.exit(1)
