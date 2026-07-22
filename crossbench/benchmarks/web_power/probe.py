# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar, Iterable

import pandas as pd
from tabulate import tabulate
from typing_extensions import override

from crossbench import path as pth
from crossbench.benchmarks.benchmark_probe import BenchmarkProbeMixin
from crossbench.parse import ObjectParser, PathParser
from crossbench.probes.probe import Probe, ProbePriority
from crossbench.probes.probe_context import EmptyProbeContext
from crossbench.probes.probe_error import ProbeMissingDataError
from crossbench.probes.results import LocalProbeResult
from crossbench.probes.trace_processor.query_config import QUERIES_DIR, \
    DeviceSpecificTraceProcessorQuery
from crossbench.probes.trace_processor.trace_processor import \
    TraceProcessorProbe

if TYPE_CHECKING:
  from crossbench.probes.results import ProbeResult
  from crossbench.runner.groups.browsers import BrowsersRunGroup
  from crossbench.runner.runner import Runner


class WebPowerProbe(BenchmarkProbeMixin, Probe):
  NAME: ClassVar = "web_power_probe"
  PRIORITY: ClassVar = ProbePriority.PRE_TRACE_PROCESSOR
  BENCHMARK_NAME: ClassVar = "WebPower"
  IS_GENERAL_PURPOSE: ClassVar = False
  PRODUCES_DATA: ClassVar = False
  INTERNAL_QUERIES_DIR: ClassVar = (
      pth.ROOT_DIR / "internal" / "probes" / "trace_processor" / "queries" /
      "web_power")

  @override
  def get_context_cls(self) -> type[EmptyProbeContext[WebPowerProbe]]:
    return EmptyProbeContext

  def _validate_and_resolve_mapping_entry(self, key: str, value: str,
                                          mapping_dir: pth.LocalPath) -> str:
    ObjectParser.regexp(key, f"mapping key '{key}'")
    sql_file = mapping_dir.parent / f"{value}.sql"
    PathParser.existing_file_path(sql_file, "Mapped SQL file")
    return str(sql_file.resolve())

  def _load_mapping(self, mapping_dir: pth.LocalPath) -> dict[str, str]:
    mapping_file = mapping_dir / "mapping.hjson"
    if not mapping_file.is_file():
      raise ValueError(f"Mapping file does not exist: {mapping_file}")
    mapping = ObjectParser.dict(ObjectParser.hjson_file(mapping_file))
    return {
        key: self._validate_and_resolve_mapping_entry(key, value, mapping_dir)
        for key, value in mapping.items()
    }

  @override
  def get_extra_probes(self, runner: Runner) -> Iterable[Probe]:
    if runner.has_probe(TraceProcessorProbe.NAME):
      return ()
    # We only need TraceProcessorProbe if we are capturing Perfetto traces.
    # Otherwise, there will be no trace to query power_rails from.
    if not runner.has_probe("perfetto"):
      return ()
    device_mapping: dict[str, str] = {}
    device_mapping.update(self._load_mapping(QUERIES_DIR / "web_power"))
    if self.INTERNAL_QUERIES_DIR.is_dir():
      device_mapping.update(self._load_mapping(self.INTERNAL_QUERIES_DIR))
    query = DeviceSpecificTraceProcessorQuery(
        name="power_rails", device_override=device_mapping)
    return (TraceProcessorProbe(
        queries=[query], module_paths=[QUERIES_DIR / "web_power"]),)

  @override
  def log_browsers_result(self, group: BrowsersRunGroup) -> None:
    result = group.results.get(self)
    if not result or not result.csv:
      return
    scores_file = result.csv
    version_str = ".".join(map(str, self.benchmark.version()))
    scores_table = tabulate(
        pd.read_csv(scores_file),
        headers="keys",
        tablefmt="plain",
        showindex=False)

    logging.critical("%s Benchmark (%s)\n"
                     "%s scores:\n"
                     "%s", self.BENCHMARK_NAME, version_str,
                     self.BENCHMARK_NAME, scores_table)

  @override
  def merge_browsers(self, group: BrowsersRunGroup) -> ProbeResult:
    result_path = group.get_local_probe_result_path(self)
    scores_file = result_path.with_name("power_scores.csv")
    self._compute_score(group).to_csv(scores_file, index=False)
    return LocalProbeResult(csv=(scores_file,))

  def _compute_score(self, group: BrowsersRunGroup) -> pd.DataFrame:
    trace_result = group.results.get_by_name("trace_processor")
    if not trace_result:
      return self._get_base_df(group)

    all_results = trace_result.csv_list
    query_results = [r for r in all_results if r.stem.endswith("power_rails")]
    if not query_results:
      return self._get_base_df(group)
    if len(query_results) > 1:
      raise ProbeMissingDataError(
          self, f"Multiple power_rails results found: {query_results}")

    query_result = query_results[0]
    df = pd.read_csv(query_result)

    # Calculate total power per run by summing avg_power_mw for each rail.
    df_sum = (
        df.groupby(["cb_browser", "cb_story",
                    "cb_run"])["avg_power_mw"].sum().reset_index())
    df_sum.rename(columns={"avg_power_mw": "total_power_mw"}, inplace=True)

    # Average total_power_mw over runs for each browser/story combination.
    run_metrics = (
        df_sum.groupby(["cb_browser",
                        "cb_story"])["total_power_mw"].mean().to_frame())

    # Update the base DataFrame with actual computed scores where available.
    # We use combine_first so that any browser/story present in base_df but
    # missing in run_metrics will be padded with NaN.
    base_df = self._get_base_df(group)
    if not base_df.empty:
      base_df = base_df.set_index(["cb_browser", "cb_story"])
      run_metrics = run_metrics.combine_first(base_df)

    return run_metrics.reset_index()

  def _get_base_df(self, group: BrowsersRunGroup) -> pd.DataFrame:
    """Create a baseline dataframe with all browser/story combinations
       padded with NaN scores. This gracefully handles unmapped devices."""
    combinations = []
    for run in group.runs:
      combinations.append({
          "cb_browser": run.browser.unique_name,
          "cb_story": run.story.name,
          "total_power_mw": float("nan"),
      })
    return pd.DataFrame(combinations).drop_duplicates()
