# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, TypeAlias

import tabulate as tbl
from typing_extensions import override

from crossbench.cli.config.network import NetworkConfig, NetworkType
from crossbench.cli.config.network_speed import NetworkSpeedConfig
from crossbench.cli.parser import CrossBenchArgumentParser
from crossbench.cli.subcommand.base import CrossbenchSubcommand
from crossbench.probes.all import GENERAL_PURPOSE_PROBES

if TYPE_CHECKING:
  import argparse
  HelpData: TypeAlias = dict[str, dict[str, Any]]


class DescribeSubcommand(CrossbenchSubcommand):

  PROBE_ALIAS = ("probe", "probes")
  BENCHMARK_ALIAS = ("benchmark", "benchmarks")
  NETWORK_ALIAS = ("network", "networks")
  CATEGORIES = ("all",) + PROBE_ALIAS + BENCHMARK_ALIAS + NETWORK_ALIAS


  def add_cli_parser(self) -> argparse.ArgumentParser:
    describe_parser = self.cli.subparsers.add_parser(
        "describe", aliases=["desc"], help="Print all benchmarks and stories")
    assert isinstance(describe_parser, CrossBenchArgumentParser)
    describe_parser.add_argument(
        "category",
        nargs="?",
        choices=self.CATEGORIES,
        default="all",
        help="Limit output to the given category, defaults to 'all'")
    describe_parser.add_argument(
        "filter",
        nargs="?",
        help=("Only display the given item from the provided category. "
              "By default all items are displayed. "
              "Example: describe probes v8.log"))
    describe_parser.add_argument(
        "--json",
        default=False,
        action="store_true",
        help="Print the data as json data")
    self.cli.add_debugging_arguments(describe_parser)
    return describe_parser

  @override
  def run(self, args: argparse.Namespace) -> None:
    self.describe(args.category, args.filter, args.json)

  def run_from_help(self, args: argparse.Namespace) -> None:
    search_terms = args.search_terms
    category = "all"
    search_str = ""
    if len(search_terms) == 1:
      search_str = search_terms[0]
    elif len(search_terms) == 2:
      category, search_str = search_terms
    else:
      self.error(f"Invalid help args: {search_terms}")
    if category not in self.CATEGORIES:
      self.error(
          f"Invalid category {repr(category)}, choices are {self.CATEGORIES}")
    self.describe(category, search_str)

  def describe(self,
               category: str,
               search_str: str | None,
               print_json: bool = False) -> None:
    category, search_str = self._process_search_str(category, search_str)

    data: HelpData = {
        "benchmarks": self._benchmark_help(search_str),
        "probes": self._probe_help(search_str),
        "networks": self._network_help(search_str)
    }
    if print_json:
      self.print_json(category, search_str, data)
      return
    # Create tabular format
    printed_any = False
    if category in ("all", "benchmark", "benchmarks"):
      printed_any |= self.print_benchmarks(category, search_str, data)
    if category in ("all", "probe", "probes"):
      printed_any |= self.print_probes(category, search_str, data)
    if category in ("all", "network", "networks"):
      printed_any |= self.print_networks(category, search_str, data)
    if not printed_any:
      self.no_match_error(search_str)

  def _process_search_str(self, category: str,
                          search_str: str | None) -> Tuple[str, str | None]:
    if not search_str:
      return category, search_str
    search_str = search_str.lower()
    if search_str in self.PROBE_ALIAS:
      category = "probe"
      search_str = None
    elif search_str in self.BENCHMARK_ALIAS:
      category = "benchmark"
      search_str = None
    elif search_str in self.NETWORK_ALIAS:
      category = "network"
      search_str = None
    return category, search_str

  def print_json(self, category: str, search_str: str | None,
                 data: HelpData) -> None:
    if category in self.PROBE_ALIAS:
      data = data["probes"]
      if not data:
        self.error(f"No matching probe found: '{search_str}'")
    elif category in self.BENCHMARK_ALIAS:
      data = data["benchmarks"]
      if not data:
        self.error(f"No matching benchmark found: '{search_str}'")
    elif category in self.NETWORK_ALIAS:
      data = data["networks"]
      if not data:
        self.error(f"No matching network found: '{search_str}'")
    else:
      assert category == "all", f"Got unknown category {category}"
      if not data["benchmarks"] and not data["probes"] and not data["networks"]:
        self.no_match_error(search_str)
    print(json.dumps(data, indent=2))

  def no_match_error(self, search_str):
    self.error(
        f"No matching benchmarks, probes or networks found: '{search_str}'")

  def print_probes(self, category: str, search_str: str | None, data: HelpData):
    printed_any: bool = False
    table = [["Probe", "Help"]]
    for probe_name, probe_desc in data["probes"].items():
      table.append([probe_name, probe_desc])
    if len(table) <= 1:
      if category != "all":
        self.error(f"No matching probe found: '{search_str}'")
    else:
      printed_any = True
      print(tbl.tabulate(table, tablefmt="grid"))
    return printed_any

  def print_benchmarks(self, category: str, search_str: str | None,
                       data: HelpData):
    printed_any = False
    table: List[List[Optional[str]]] = [["Benchmark", "Property", "Value"]]
    for benchmark_name, values in data["benchmarks"].items():
      table.append([
          benchmark_name,
      ])
      for name, value in values.items():
        if isinstance(value, (tuple, list)):
          value = "\n".join(value)
        elif isinstance(value, dict):
          if not value.items():
            value = "[]"
          else:
            kwargs = {"maxcolwidths": 60}
            value = tbl.tabulate(value.items(), tablefmt="plain", **kwargs)
        table.append([None, name, value])
    if len(table) <= 1:
      if category != "all":
        self.error(f"No matching benchmark found: '{search_str}'")
    else:
      printed_any = True
      print(tbl.tabulate(table, tablefmt="grid"))
    return printed_any

  def print_networks(self, category: str, search_str: str | None,
                     data: HelpData):
    printed_any: bool = False
    table = [["Network", "Help"]]
    for network_name, network_desc in data["networks"].items():
      table.append([network_name, network_desc])
    if len(table) <= 1:
      if category != "all":
        self.error(f"No matching network found: '{search_str}'")
    else:
      printed_any = True
      print(tbl.tabulate(table, tablefmt="grid"))
    return printed_any

  def _benchmark_help(
      self,
      search_str: Optional[str] = None,
  ) -> dict[str, Any]:
    benchmarks_data: dict[str, Any] = {}
    for benchmark_cls in self.cli.BENCHMARKS:
      aliases: Tuple[str, ...] = benchmark_cls.aliases()
      if search_str:
        if benchmark_cls.NAME != search_str and search_str not in aliases:
          continue
      benchmark_info = benchmark_cls.describe()
      benchmark_info["help"] = f"See `{benchmark_cls.NAME} --help`"
      benchmarks_data[benchmark_cls.NAME] = benchmark_info
    return benchmarks_data

  def _probe_help(self, search_str: str | None) -> dict[str, Any]:
    probe_data: dict[str, Any] = {
        str(probe_cls.NAME): probe_cls.help_text()
        for probe_cls in GENERAL_PURPOSE_PROBES
        if not search_str or probe_cls.NAME == search_str
    }
    return probe_data

  def _network_help(self, search_str: str | None) -> dict[str, Any]:
    network_data: dict[str, Any] = {
        network_type.name: network_type.help
        for network_type in NetworkType  # pytype: disable=missing-parameter
        if not search_str or network_type.name.lower() == search_str
    }
    # Print config details if any network info is returned.
    if network_data:
      network_data["Config"] = NetworkConfig.help()
      network_data["Speed"] = NetworkSpeedConfig.help()
    return network_data
