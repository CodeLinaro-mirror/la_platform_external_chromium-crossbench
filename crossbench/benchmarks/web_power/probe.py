# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar, Iterable

import pandas as pd
from perfetto.batch_trace_processor.api import BatchTraceProcessor, \
    BatchTraceProcessorConfig
from perfetto.trace_processor.api import TraceProcessorConfig
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


def _mean_without_outliers(group: pd.Series) -> float:
  """Computes the mean, discarding top and bottom outliers for >=5 runs."""
  if len(group) >= 5:
    return group.sort_values().iloc[1:-1].mean()
  return group.mean()


class WebPowerProbe(BenchmarkProbeMixin, Probe):
  NAME: ClassVar = "web_power_probe"
  PRIORITY: ClassVar = ProbePriority.PRE_TRACE_PROCESSOR
  BENCHMARK_NAME: ClassVar = "WebPower"
  IS_GENERAL_PURPOSE: ClassVar = False
  PRODUCES_DATA: ClassVar = False
  INTERNAL_QUERIES_DIR: ClassVar = (
      pth.ROOT_DIR / "internal" / "probes" / "trace_processor" / "queries" /
      "web_power")
  QUERY_NAME: ClassVar = "power_rails"

  @override
  def get_context_cls(self) -> type[EmptyProbeContext[WebPowerProbe]]:
    return EmptyProbeContext

  @classmethod
  def _validate_and_resolve_mapping_entry(cls, key: str, value: str,
                                          mapping_dir: pth.LocalPath) -> str:
    ObjectParser.regexp(key, f"mapping key '{key}'")
    sql_file = mapping_dir.parent / f"{value}.sql"
    PathParser.existing_file_path(sql_file, "Mapped SQL file")
    return str(sql_file.resolve())

  @classmethod
  def _load_mapping(cls, mapping_dir: pth.LocalPath) -> dict[str, str]:
    mapping_file = mapping_dir / "mapping.hjson"
    if not mapping_file.is_file():
      raise ValueError(f"Mapping file does not exist: {mapping_file}")
    mapping = ObjectParser.dict(ObjectParser.hjson_file(mapping_file))
    return {
        key: cls._validate_and_resolve_mapping_entry(key, value, mapping_dir)
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
    return (TraceProcessorProbe(
        queries=[self._get_query_config()],
        module_paths=[QUERIES_DIR / "web_power"]),)

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
    query_results = [r for r in all_results if r.stem.endswith(self.QUERY_NAME)]
    if not query_results:
      return self._get_base_df(group)
    if len(query_results) > 1:
      raise ProbeMissingDataError(
          self, f"Multiple {self.QUERY_NAME} results found: {query_results}")

    return self.process_result_dir(
        group.get_local_probe_result_path(self).parent,
        self._get_base_df(group))

  @classmethod
  def _get_power_rails_data(
      cls, result_dir: pth.LocalPath, base_df: pd.DataFrame,
      reprocess: bool) -> tuple[pd.DataFrame | None, pd.DataFrame]:
    if reprocess:
      return cls._reprocess_traces(result_dir, base_df), base_df

    csv_path = result_dir / "trace_processor" / f"{cls.QUERY_NAME}.csv"
    if not csv_path.is_file():
      if "total_power_mw" not in base_df.columns:
        base_df = base_df.copy()
        base_df["total_power_mw"] = "No Data"
      return None, base_df
    return pd.read_csv(csv_path), base_df

  @classmethod
  def process_result_dir(cls,
                         result_dir: pth.LocalPath,
                         base_df: pd.DataFrame,
                         reprocess: bool = False) -> pd.DataFrame:
    df, base_df = cls._get_power_rails_data(result_dir, base_df, reprocess)
    if df is None:
      return base_df

    # Calculate total power per run by summing avg_power_mw for each rail.
    df_sum = (
        df.groupby(["cb_browser", "cb_story",
                    "cb_run"])["avg_power_mw"].sum().reset_index())
    df_sum.rename(columns={"avg_power_mw": "total_power_mw"}, inplace=True)

    # Average total_power_mw over runs for each browser/story combination.
    run_metrics = (
        df_sum.groupby([
            "cb_browser", "cb_story"
        ])["total_power_mw"].agg(_mean_without_outliers).to_frame())

    # Update the base DataFrame with actual computed scores where available.
    # We use combine_first so that any browser/story present in base_df but
    # missing in run_metrics will be padded with NaN.
    if not base_df.empty:
      base_df = base_df.set_index(["cb_browser", "cb_story"])
      run_metrics = run_metrics.combine_first(base_df)

    return run_metrics.reset_index()

  @classmethod
  def _get_query_config(cls) -> DeviceSpecificTraceProcessorQuery:
    mapping = cls._load_mapping(QUERIES_DIR / "web_power")
    if cls.INTERNAL_QUERIES_DIR.is_dir():
      mapping.update(cls._load_mapping(cls.INTERNAL_QUERIES_DIR))

    return DeviceSpecificTraceProcessorQuery(
        name=cls.QUERY_NAME, device_override=mapping)

  @classmethod
  def _get_traces(cls, result_dir: pth.LocalPath) -> list[pth.LocalPath]:
    allowed_exts = (".perfetto-trace", ".perfetto-trace.gz", ".pb", ".pb.gz")
    return [
        t for t in result_dir.glob("*/stories/*/*/*/*")
        if t.is_file() and t.name.endswith(allowed_exts)
    ]

  @classmethod
  def _reprocess_traces(cls, result_dir: pth.LocalPath,
                        base_df: pd.DataFrame) -> pd.DataFrame:
    traces = cls._get_traces(result_dir)
    if not traces:
      raise ValueError(f"No traces found in {result_dir} to reprocess.")

    btp_config = BatchTraceProcessorConfig(
        tp_config=TraceProcessorConfig(
            extra_flags=["--add-sql-package",
                         str(QUERIES_DIR / "web_power")]))
    query_config = cls._get_query_config()

    browser_to_model = base_df.set_index("cb_browser")["device_model"].to_dict()

    sql_to_traces: dict[str, list[str]] = {}
    trace_to_meta: dict[str, tuple[str, str, int]] = {}

    for trace in traces:
      cb_browser, _, cb_story, cb_run, *_ = trace.parent.relative_to(
          result_dir).parts

      device_model = browser_to_model[cb_browser]

      resolved = query_config.resolve_for_device_model(device_model)
      if not resolved:
        logging.error("Unsupported device model: %s", device_model)
        continue

      str_trace = str(trace)
      sql_to_traces.setdefault(resolved.sql, []).append(str_trace)
      trace_to_meta[str_trace] = (cb_browser, cb_story, int(cb_run))

    meta_df = pd.DataFrame.from_dict(
        trace_to_meta,
        orient="index",
        columns=["cb_browser", "cb_story", "cb_run"])

    df_list = []
    for sql, batch_traces in sql_to_traces.items():
      with BatchTraceProcessor(traces=batch_traces, config=btp_config) as btp:
        res_df = btp.query_and_flatten(sql)
        if res_df.empty or "_path" not in res_df.columns:
          continue

        if "trace" in res_df.columns:
          res_df = res_df.drop(columns=["trace"])

        res_df = res_df.merge(meta_df, left_on="_path", right_index=True)
        res_df = res_df.drop(columns=["_path"])
        df_list.append(res_df)

    return pd.concat(df_list, ignore_index=True)

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
