# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench.cli.parser import CrossBenchArgumentParser
from crossbench.cli.subcommand.base import CrossbenchSubcommand
from crossbench.parse import NumberParser
from crossbench.pinpoint.job_config import job_config
from crossbench.pinpoint.list_format import ListFormatEnum
from crossbench.pinpoint.list_jobs import list_jobs
from crossbench.pinpoint.user import UserEnum, list_user

if TYPE_CHECKING:
  import argparse

  from crossbench.cli.cli import CrossBenchCLI
  from crossbench.cli.types import Subparsers


class PinpointBaseSubcommand(abc.ABC):

  def __init__(self, parent: PinpointSubcommand) -> None:
    self._parent = parent
    self._parser = self.add_cli_parser()
    self._parser.set_defaults(pinpoint_subcommand=self)

  @abc.abstractmethod
  def add_cli_parser(self) -> argparse.ArgumentParser:
    raise NotImplementedError

  @abc.abstractmethod
  def run(self, args: argparse.Namespace) -> None:
    raise NotImplementedError


class PinpointListSubcommand(PinpointBaseSubcommand):
  """A subcommand for interacting with the Pinpoint service."""

  @override
  def add_cli_parser(self) -> argparse.ArgumentParser:
    list_parser = self._parent.subparsers.add_parser(
        "list", aliases=("ls",), help="Displays recent Pinpoint jobs.")
    list_parser.add_argument(
        "--user",
        "-u",
        type=list_user,
        default=UserEnum.ME,
        help=("Filter jobs by user. 'me' (default) shows jobs for your "
              "@google.com and @chromium.org accounts, derived from your "
              "authenticated username. 'all' shows jobs from all users. "
              "An email address can also be specified. Note: 'me' might not "
              "work correctly if your usernames differ across domains."))
    list_parser.add_argument(
        "--number",
        "-n",
        type=NumberParser.positive_int,
        default=20,
        help="The maximum number of jobs to fetch and display. (default: 20)")
    list_parser.add_argument(
        "--format",
        "-f",
        choices=[
            ListFormatEnum.TABLE, ListFormatEnum.JSON, ListFormatEnum.YAML,
            ListFormatEnum.CSV, ListFormatEnum.TSV
        ],
        default=ListFormatEnum.TABLE,
        help="The output format for the list of jobs. (default: table)")
    list_parser.add_argument(
        "--truncate",
        "-t",
        type=NumberParser.positive_int,
        default=None,
        help=("Truncate cell content to the specified maximum length. "
              "Only applies to the 'table' format."))
    return list_parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    list_jobs(args.user, args.number, args.truncate, args.format)


class PinpointConfigSubcommand(PinpointBaseSubcommand):
  """Get the configuration of a specific Pinpoint job."""

  @override
  def add_cli_parser(self) -> argparse.ArgumentParser:
    config_parser = self._parent.subparsers.add_parser(
        "config",
        aliases=("cfg",),
        help="Get the configuration of a specific Pinpoint job.")
    config_parser.add_argument(
        "--id",
        required=True,
        help="The ID of the job to get the configuration for.")
    return config_parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    job_config(args.id)


class PinpointSubcommand(CrossbenchSubcommand):
  """A subcommand for interacting with the Pinpoint service."""

  def __init__(self, cli: CrossBenchCLI) -> None:
    super().__init__(cli)
    self._subparsers = self.parser.add_subparsers(
        parser_class=CrossBenchArgumentParser,
        dest="action",
        required=True,
        help="Pinpoint actions")
    self._list_subcommand = PinpointListSubcommand(self)
    self._config_subcommand = PinpointConfigSubcommand(self)

  @property
  def subparsers(self) -> Subparsers:
    return self._subparsers

  @override
  def add_cli_parser(self) -> argparse.ArgumentParser:
    pinpoint_parser = self.cli.subparsers.add_parser(
        "pinpoint", aliases=("pp",), help="Interact with the Pinpoint service.")
    assert isinstance(pinpoint_parser, CrossBenchArgumentParser)
    return pinpoint_parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    args.pinpoint_subcommand.run(args)
