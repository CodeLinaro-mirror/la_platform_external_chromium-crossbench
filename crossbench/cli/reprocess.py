# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING, Any, Sequence

import pandas as pd
from tabulate import tabulate

from crossbench.benchmarks.web_power.probe import WebPowerProbe
from crossbench.cli.btp import DEFAULT_RESULT_DIR
from crossbench.cli.parser import CBArgumentParser
from crossbench.parse import ObjectParser, PathParser

if TYPE_CHECKING:
  from crossbench import path as pth
  from crossbench.probes.probe import Probe


class ReprocessUtil:
  """Utility class for reprocessing existing Crossbench benchmark data offline.

  This is used by the `cb_reprocess` CLI tool to re-evaluate probe scores
  (e.g., parsing power rails) from previously collected CSV files without
  needing to re-run the entire benchmark.
  """

  SUPPORTED_PROBES: dict[str, type[Probe]] = {
      "web_power": WebPowerProbe,
  }

  def __init__(self) -> None:
    self.parser: CBArgumentParser = CBArgumentParser(
        description=(
            "Reprocesses benchmark results "
            "from existing CSV files without re-running the benchmark."),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    self.parser.add_argument(
        "path",
        type=PathParser.dir_path,
        nargs="?",
        default=DEFAULT_RESULT_DIR,
        help="Path to the benchmark result directory.")
    self.parser.add_argument(
        "--probe",
        "--probes",
        type=self._parse_probes,
        default=list(self.SUPPORTED_PROBES.keys()),
        help="Comma-separated list of probes to reprocess.")

  def _parse_probes(self, value: str) -> list[str]:
    probes = ObjectParser.str_list(value, "probes")
    for probe in probes:
      if probe not in self.SUPPORTED_PROBES:
        raise argparse.ArgumentTypeError(f"Unsupported probe: '{probe}'")
    return probes

  def run(self, argv: Sequence[str]) -> None:
    args: argparse.Namespace = self.parser.parse_args(argv)

    result_dir: pth.LocalPath = args.path
    probe_names: list[str] = args.probe

    base_df: pd.DataFrame = self._get_base_df(result_dir)
    for probe_name in probe_names:
      self._process_probe(probe_name, result_dir, base_df)

  def _process_probe(self, probe_name: str, result_dir: pth.LocalPath,
                     base_df: pd.DataFrame) -> None:
    probe_cls: type[Probe] = self.SUPPORTED_PROBES[probe_name]
    # TODO: Upstream this to the base Probe interface or find an alternative to
    # unify offline reprocessing across all probes.
    assert hasattr(probe_cls, "process_result_dir")
    new_scores: pd.DataFrame = probe_cls.process_result_dir(
        result_dir, base_df, reprocess=True)
    print(
        tabulate(new_scores, headers="keys", tablefmt="plain", showindex=False))

  @classmethod
  def _get_device_model_from_run(cls, run_dir: pth.LocalPath) -> str:
    for json_name, keys in (("cb.system.details.json",
                             ["Android", "ro.product.model"]),
                            ("cb.results.json", ["browser", "os", "model"])):
      file_path = run_dir / json_name
      if not file_path.is_file():
        continue
      data = json.loads(file_path.read_text(encoding="utf-8"))
      for key in keys:
        data = data.get(key) if isinstance(data, dict) else ""
      if data:
        return data
    return ""

  def _get_base_df(self, result_dir: pth.LocalPath) -> pd.DataFrame:
    # Reconstruct the base_df by scanning the result-dir for browser and story
    # combinations.
    combinations: list[dict[str, Any]] = []
    # Glob exactly 5 levels deep to reach leaf run directories.
    for run_dir in result_dir.glob("*/stories/*/*/*/"):
      try:
        rel_parts: tuple[str, ...] = run_dir.relative_to(result_dir).parts
      except ValueError:
        continue

      # rel_parts: (`browser`, "stories", `story`, `run`, `probe`).
      if len(rel_parts) == 5 and rel_parts[1] == "stories":
        combinations.append({
            "device_model": self._get_device_model_from_run(run_dir),
            "cb_browser": rel_parts[0],
            "cb_story": rel_parts[2],
        })

    return pd.DataFrame(combinations).drop_duplicates()
