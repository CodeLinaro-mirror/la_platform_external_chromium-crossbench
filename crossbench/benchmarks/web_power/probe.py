# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, ClassVar, Iterable

import pandas as pd
from tabulate import tabulate
from typing_extensions import override

from crossbench.benchmarks.benchmark_probe import BenchmarkProbeMixin
from crossbench.probes.probe import Probe, ProbePriority
from crossbench.probes.probe_context import ProbeContext
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


class WebPowerProbeContext(ProbeContext["WebPowerProbe"]):

  def start(self) -> None:
    pass

  def stop(self) -> None:
    pass

  def teardown(self) -> ProbeResult:
    return self.empty_result()


class WebPowerProbe(BenchmarkProbeMixin, Probe):
  NAME: ClassVar = "web_power_probe"
  PRIORITY: ClassVar = ProbePriority.PRE_TRACE_PROCESSOR
  BENCHMARK_NAME: ClassVar = "WebPower"
  IS_GENERAL_PURPOSE: ClassVar = False
  PRODUCES_DATA: ClassVar = False

  @override
  def get_context_cls(self) -> type[WebPowerProbeContext]:
    return WebPowerProbeContext

  @override
  def get_extra_probes(self, runner: Runner) -> Iterable[Probe]:
    if runner.has_probe(TraceProcessorProbe.NAME):
      return ()
    mapping_file = QUERIES_DIR / "web_power/mapping.json"
    with mapping_file.open("r", encoding="utf-8") as f:
      device_mapping = json.load(f)

    queries = [
        DeviceSpecificTraceProcessorQuery(
            name="power_rails", device_override=device_mapping)
    ]
    return (TraceProcessorProbe(queries=queries),)

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
      raise ProbeMissingDataError(self,
                                  f"{group} has no TraceProcessorProbe result")
    all_results = trace_result.csv_list
    query_results = [r for r in all_results if r.stem.endswith("power_rails")]
    if not query_results:
      raise ProbeMissingDataError(self, "power_rails result not found")
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
                        "cb_story"])["total_power_mw"].mean().reset_index())
    return run_metrics
