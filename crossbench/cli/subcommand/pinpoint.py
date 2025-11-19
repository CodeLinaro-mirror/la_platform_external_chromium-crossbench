# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import argparse
from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench.cli.parser import CrossBenchArgumentParser
from crossbench.cli.subcommand.base import CrossbenchSubcommand
from crossbench.parse import NumberParser
from crossbench.pinpoint.cancel_job import cancel_job
from crossbench.pinpoint.config import PinpointTryJobConfig
from crossbench.pinpoint.job_config import job_config
from crossbench.pinpoint.list_benchmarks import fetch_benchmarks
from crossbench.pinpoint.list_bots import fetch_bots
from crossbench.pinpoint.list_builds import list_builds
from crossbench.pinpoint.list_format import ListFormatEnum
from crossbench.pinpoint.list_jobs import list_jobs
from crossbench.pinpoint.list_stories import fetch_stories
from crossbench.pinpoint.start_job import start_job
from crossbench.pinpoint.user import UserEnum, list_user

if TYPE_CHECKING:
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


class PinpointStartSubcommand:
  """Starts a new Pinpoint job."""

  def __init__(self, parent: PinpointSubcommand) -> None:
    self._parent = parent
    self._parser = self.add_cli_parser()
    self._parser.set_defaults(pinpoint_subcommand=self)

  def add_cli_parser(self) -> argparse.ArgumentParser:
    start_parser = self._parent.subparsers.add_parser(
        "start",
        help="Starts a new Pinpoint A/B job.",
        description="Starts a new Pinpoint A/B job. "
        "This command allows you to specify two configurations (base and "
        "experiment) to compare performance between them.",
        epilog="""Example:
  pinpoint start \\
    --benchmark=speedometer3.crossbench \\
    --bot=linux-r350-perf \\
    --story=default \\
    --story-tags=mobile,desktop \\
    --repeat=20 \\
    --bug-id=123456 \\
    --base-commit=HEAD \\
    --exp-commit=recent \\
    --base-patch-url=https://chromium-review.googlesource.com/c/v8/v8/+/12345 \\
    --exp-patch-url=https://chromium-review.googlesource.com/c/v8/v8/+/67890 \\
    --base-js-flags=--flag1,--flag2 \\
    --exp-js-flags=--flag3,--flag4 \\
    --base-enable-features=feature1,feature2 \\
    --exp-enable-features=feature3,feature4 \\
    --base-disable-features=feature5,feature6 \\
    --exp-disable-features=feature7,feature8
""",
        formatter_class=argparse.RawTextHelpFormatter)
    start_parser.add_argument(
        "--config",
        help="A try job configuration in the JSON/HJSON format. "
        "Accepts a path to a configuration file, or configuration string. "
        "If the same argument is specified in the config and then provided "
        "as a command line argument, the latter overrides the former. "
        "Get more information by running `describe PinpointTryJobConfig`")
    start_parser.add_argument("--benchmark", help="The benchmark to run.")
    start_parser.add_argument(
        "--bot",
        help="The bot configuration to run on (e.g., 'linux-perf').")
    start_parser.add_argument("--story", help="The story to run.")
    start_parser.add_argument(
        "--story-tags",
        dest="story_tags",
        help="Story tags to filter stories.")
    start_parser.add_argument(
        "--repeat",
        type=NumberParser.positive_int,
        help="How many times to repeat the experiment.")
    start_parser.add_argument(
        "--bug",
        type=NumberParser.positive_int,
        help="The bug ID to associate with the job.")
    start_parser.add_argument(
        "--base-commit",
        help="Git commit hash for the base build. Accepts a commit hash, "
        "'HEAD' (latest commit), or 'recent' (the most recent build). "
        "Defaults to HEAD.")
    start_parser.add_argument(
        "--exp-commit",
        help="Git commit hash for the experiment build. Accepts a commit hash, "
        "'HEAD' (latest commit), or 'recent' (the most recent build).")
    start_parser.add_argument(
        "--base-patch",
        help="Gerrit URL of a patch to apply to the base commit.")
    start_parser.add_argument(
        "--exp-patch",
        help="Gerrit URL of a patch to apply to the experiment commit.")

    # Extra browser args.
    start_parser.add_argument(
        "--base-js-flags",
        help="JavaScript flags to pass to V8 for the base commit. "
        "Example: --base-js-flags=--turbolev-future")
    start_parser.add_argument(
        "--exp-js-flags",
        help="JavaScript flags to pass to V8 for the experiment commit. "
        "Example: --exp-js-flags=--turbolev-future")
    start_parser.add_argument(
        "--base-enable-features",
        help="Comma-separated list of Chrome features to enable for the base "
        "commit. Example: --base-enable-features=Feature1,Feature2")
    start_parser.add_argument(
        "--exp-enable-features",
        help="Comma-separated list of Chrome features to enable for the "
        "experiment commit. Example: --exp-enable-features=FeatureA,FeatureB")
    start_parser.add_argument(
        "--base-disable-features",
        help="Comma-separated list of Chrome features to disable for the base "
        "commit. Example: --base-disable-features=Feature1,Feature2")
    start_parser.add_argument(
        "--exp-disable-features",
        help="Comma-separated list of Chrome features to disable for the "
        "experiment commit. Example: --exp-disable-features=FeatureA,FeatureB")

    return start_parser

  def run(self, args: argparse.Namespace) -> None:
    config = PinpointTryJobConfig.parse_and_override(
        config=args.config,
        benchmark=args.benchmark,
        bot=args.bot,
        story=args.story,
        story_tags=args.story_tags,
        repeat=args.repeat,
        bug=args.bug,
        base_commit=args.base_commit,
        exp_commit=args.exp_commit,
        base_patch=args.base_patch,
        exp_patch=args.exp_patch,
    )
    start_job(
        config=config,
        base_js_flags=args.base_js_flags,
        exp_js_flags=args.exp_js_flags,
        base_enable_features=args.base_enable_features,
        exp_enable_features=args.exp_enable_features,
        base_disable_features=args.base_disable_features,
        exp_disable_features=args.exp_disable_features,
    )


class PinpointCancelSubcommand(PinpointBaseSubcommand):
  """Cancel a specific Pinpoint job."""

  @override
  def add_cli_parser(self) -> argparse.ArgumentParser:
    cancel_parser = self._parent.subparsers.add_parser(
        "cancel", help="Cancel a specific Pinpoint job.")
    cancel_parser.add_argument(
        "--id", required=True, help="The ID of the job to cancel.")
    cancel_parser.add_argument(
        "--reason",
        required=False,
        default="Cancelled via Pinpoint CLI.",
        help="Reason for cancellation.")
    return cancel_parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    cancel_job(args.id, args.reason)


class PinpointBaseFilteredListSubcommand(PinpointBaseSubcommand):
  """Base subcommand class for displaying filtered string lists."""

  @override
  def add_cli_parser(self) -> argparse.ArgumentParser:
    parser = self.create_parser()
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help=("Filter results by a case-insensitive substring match. "
              "Only items containing the filter string will be shown."))
    return parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    items = self.fetch_list(args)
    filter_str = (args.filter or "").lower().strip()
    filtered_items = [item for item in items if filter_str in item.lower()]
    print("\n".join(filtered_items))

  @abc.abstractmethod
  def create_parser(self) -> argparse.ArgumentParser:
    pass

  @abc.abstractmethod
  def fetch_list(self, args: argparse.Namespace) -> list[str]:
    pass


class PinpointBotsSubcommand(PinpointBaseFilteredListSubcommand):
  """A subcommand for displaying available Pinpoint bots."""

  @override
  def create_parser(self) -> argparse.ArgumentParser:
    bots_parser = self._parent.subparsers.add_parser(
        "bots", help="Displays all available Pinpoint bots.")
    return bots_parser

  @override
  def fetch_list(self, args: argparse.Namespace) -> list[str]:
    return fetch_bots()


class PinpointBenchmarksSubcommand(PinpointBaseFilteredListSubcommand):
  """A subcommand for displaying available Pinpoint benchmarks."""

  @override
  def create_parser(self) -> argparse.ArgumentParser:
    benchmarks_parser = self._parent.subparsers.add_parser(
        "benchmarks", help="Displays all available Pinpoint benchmarks.")
    return benchmarks_parser

  @override
  def fetch_list(self, args: argparse.Namespace) -> list[str]:
    return fetch_benchmarks()


class PinpointStoriesSubcommand(PinpointBaseFilteredListSubcommand):
  """A subcommand for displaying available stories for a Pinpoint benchmark."""

  @override
  def create_parser(self) -> argparse.ArgumentParser:
    stories_parser = self._parent.subparsers.add_parser(
        "stories",
        help="Displays all available stories for a Pinpoint benchmark.")
    stories_parser.add_argument(
        "benchmark", help="The benchmark for which to list stories.")
    return stories_parser

  @override
  def fetch_list(self, args: argparse.Namespace) -> list[str]:
    return fetch_stories(args.benchmark)


class PinpointBuildsSubcommand(PinpointBaseSubcommand):
  """Displays recent successful builds for a given bot."""

  @override
  def add_cli_parser(self) -> argparse.ArgumentParser:
    builds_parser = self._parent.subparsers.add_parser(
        "builds", help="Displays recent successful builds for a given bot.")
    builds_parser.add_argument(
        "bot", help="The bot configuration name (e.g., 'linux-r350-perf').")
    builds_parser.add_argument(
        "--limit",
        "-l",
        type=NumberParser.positive_int,
        default=10,
        help="Limits the number of recent builds to display. (default: 10)")
    return builds_parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    list_builds(args.bot, args.limit)


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
    self._start_subcommand = PinpointStartSubcommand(self)
    self._cancel_subcommand = PinpointCancelSubcommand(self)
    self._bots_subcommand = PinpointBotsSubcommand(self)
    self._benchmarks_subcommand = PinpointBenchmarksSubcommand(self)
    self._stories_subcommand = PinpointStoriesSubcommand(self)
    self._builds_subcommand = PinpointBuildsSubcommand(self)

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
