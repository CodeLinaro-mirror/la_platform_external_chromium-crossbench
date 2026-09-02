# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import enum
import re
import tempfile
import typing
import unittest
from typing import TYPE_CHECKING, Callable
from unittest import mock

import pandas as pd
import pytest

from crossbench import path as pth
from crossbench.benchmarks.web_power.base import VERSION_STRING
from crossbench.benchmarks.web_power.probe import WebPowerProbe
from crossbench.exception import MultiException
from crossbench.probes.bits import BitsProbe
from crossbench.probes.probe_context import EmptyProbeContext
from crossbench.probes.probe_error import ProbeMissingDataError
from crossbench.probes.trace_processor.constants import QUERIES_DIR
from crossbench.probes.trace_processor.query_config import \
    DeviceSpecificTraceProcessorQuery
from crossbench.probes.trace_processor.trace_processor import \
    TraceProcessorProbe

if TYPE_CHECKING:
  from crossbench.probes.probe import Probe

from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


class WebPowerProbeTestCase(CrossbenchFakeFsTestCase):

  def setUp(self):
    super().setUp()
    self.mock_benchmark = mock.MagicMock(bits_probe=None)
    self.mock_benchmark.version.return_value = tuple(
        map(int, VERSION_STRING.split(".")))
    self.probe = WebPowerProbe(benchmark=self.mock_benchmark)
    self.group = mock.MagicMock()
    self.group.results = mock.MagicMock()
    self.runner = mock.MagicMock()
    # Simulate that only the "perfetto" probe is attached.
    self.runner.has_probe.side_effect = lambda name: name == "perfetto"

  def _benchmark_version_str(self) -> str:
    return ".".join(map(str, self.mock_benchmark.version()))

  def _assert_log_browsers_result(self, critical_mock: mock.MagicMock) -> str:
    critical_mock.assert_called_once_with(
        "%s Benchmark (%s)\n%s scores:\n%s",
        self.probe.BENCHMARK_NAME,
        self._benchmark_version_str(),
        self.probe.BENCHMARK_NAME,
        mock.ANY,
    )
    return str(critical_mock.call_args.args[-1])

  def test_get_context_cls(self):
    """Verify that the probe uses the correct context class."""
    self.assertEqual(self.probe.get_context_cls(), EmptyProbeContext)
    hints = typing.get_type_hints(self.probe.get_context_cls)
    self.assertEqual(hints["return"], type[EmptyProbeContext[WebPowerProbe]])

  @mock.patch("logging.critical")
  def test_log_browsers_result_missing_data(self, critical_mock):
    """Simulate missing probe data (e.g., if the run aborted early or the probe
    was disabled)."""
    self.group.results.get.return_value = None

    # We expect an early return (silent failure) without printing any banner.
    self.probe.log_browsers_result(self.group)
    critical_mock.assert_not_called()

  @mock.patch("logging.critical")
  def test_log_browsers_result_missing_csv(self, critical_mock):
    """Simulate the probe completing, but failing to generate its final CSV
    file (e.g., due to a data processing error)."""
    self.group.results.get.return_value = mock.MagicMock(csv=None)

    # We expect an early return (silent failure) without printing any banner.
    self.probe.log_browsers_result(self.group)
    critical_mock.assert_not_called()

  @mock.patch("logging.critical")
  def test_log_browsers_result_success(self, critical_mock):
    """Simulate a successful benchmark run where the final score CSV is
    generated as expected."""
    csv_file = pth.LocalPath("power_scores.csv")
    self.fs.create_file(
        csv_file, contents="browser,story,score\n"
        "chrome,test,10\n")
    self.group.results.get.return_value = mock.MagicMock(csv=csv_file)

    self.probe.log_browsers_result(self.group)
    self.assertRegex(
        self._assert_log_browsers_result(critical_mock),
        r"^browser\s+story\s+score\s*\nchrome\s+test\s+10\s*$")

  @mock.patch("logging.critical")
  def test_log_browsers_result_bits_success(self, critical_mock):
    csv_file = pth.LocalPath("power_scores.csv")
    self.fs.create_file(
        csv_file,
        contents="cb_browser,cb_story,bits_cpu_mw,bits_soc_total_mw\n"
        "chrome,test,1020.796,1925.195\n")
    self.group.results.get.return_value = mock.MagicMock(csv=csv_file)

    self.probe.log_browsers_result(self.group)
    self.assertRegex(
        self._assert_log_browsers_result(critical_mock),
        r"^cb_browser\s+cb_story\s+bits_cpu_mw\s+bits_soc_total_mw\s*\n"
        r"chrome\s+test\s+1020\.8\s+1925\.19\s*$")

  def _extract_csv_records(
      self, result, metrics: tuple[str,
                                   ...] = ("odpm_total_mw",)) -> list[dict]:
    self.assertTrue(result.csv)
    self.assertEqual(result.csv, pth.LocalPath("results_dir/power_scores.csv"))
    df = pd.read_csv(result.csv)

    # Verify schema.
    self.assertEqual(
        list(df.columns),
        [
            "cb_browser", "cb_story", "odpm_total_mw", "bits_cpu_mw",
            "bits_soc_total_mw"
        ],
    )

    # Default to NaN.
    for col in ("odpm_total_mw", "bits_cpu_mw", "bits_soc_total_mw"):
      if col not in metrics:
        self.assertTrue(df[col].isna().all())

    keep_cols = ["cb_browser", "cb_story", *metrics]
    df = df[keep_cols].sort_values(by=["cb_browser", "cb_story"]).reset_index(
        drop=True)
    return df.to_dict(orient="records")

  def _test_merge_browsers_bits(
      self,
      bits_files: dict[pth.LocalPath, str] | None = None,
      tp_csv_contents: str | None = None,
      metrics: tuple[str, ...] = ("bits_cpu_mw", "bits_soc_total_mw"),
  ) -> list[dict]:
    result_path = pth.LocalPath("results_dir/web_power_probe")
    self.fs.create_dir(result_path.parent)
    self.group.get_local_probe_result_path.return_value = result_path

    if tp_csv_contents is not None:
      tp_result = mock.MagicMock()
      tp_csv = pth.LocalPath("results_dir/trace_processor/power_rails.csv")
      self.fs.create_file(tp_csv, contents=tp_csv_contents)
      tp_result.csv_list = [tp_csv]
      self.group.results.get_by_name.side_effect = (
          lambda name: tp_result if name == "trace_processor" else None)
    else:
      self.group.results.get_by_name.return_value = None

    for path, contents in (bits_files or {}).items():
      self.fs.create_file(path, contents=contents)

    result = self.probe.merge_browsers(self.group)
    return self._extract_csv_records(result, metrics)

  def _test_merge_browsers(
      self,
      csv_contents: str,
      metrics: tuple[str, ...] = ("odpm_total_mw",),
  ) -> list[dict]:
    return self._test_merge_browsers_bits(
        tp_csv_contents=csv_contents,
        metrics=metrics,
    )

  def test_merge_browsers_single_run(self):
    """Simulate a single benchmark run being successfully merged.
    The multiple rows represent different power rails (e.g., CPU, Display)."""
    csv_contents = ("cb_browser,cb_story,cb_run,name,avg_power_mw\n"
                    "chrome,test,0,rail_1,10.0\n"
                    "chrome,test,0,rail_2,20.0\n")
    records = self._test_merge_browsers(csv_contents)
    self.assertEqual(records, [
        {
            "cb_browser": "chrome",
            "cb_story": "test",
            "odpm_total_mw": 10.0 + 20.0
        },
    ])

  def test_merge_browsers_multiple_runs(self):
    """Simulate multiple benchmark runs (repetitions) being correctly merged and
    averaged across their power rails."""
    csv_contents = ("cb_browser,cb_story,cb_run,name,avg_power_mw\n"
                    "chrome,test,0,rail_1,10.0\n"
                    "chrome,test,0,rail_2,20.0\n"
                    "chrome,test,1,rail_1,200.0\n"
                    "chrome,test,1,rail_2,400.0\n")
    records = self._test_merge_browsers(csv_contents)
    self.assertEqual(records, [
        {
            "cb_browser": "chrome",
            "cb_story": "test",
            "odpm_total_mw": ((10.0 + 20.0) + (200.0 + 400.0)) / 2.0
        },
    ])

  def test_merge_browsers_four_runs_simple_mean(self):
    """Verify that if there are 4 or less runs, all totals are kept and averaged
    without discarding outliers."""
    csv_contents = (
        "cb_browser,cb_story,cb_run,name,avg_power_mw\n"
        # Run 0
        "chrome,test,0,rail_1,10.0\n"
        "chrome,test,0,rail_2,20.0\n"
        # Run 1
        "chrome,test,1,rail_1,30.0\n"
        "chrome,test,1,rail_2,40.0\n"
        # Run 2
        "chrome,test,2,rail_1,50.0\n"
        "chrome,test,2,rail_2,60.0\n"
        # Run 3
        "chrome,test,3,rail_1,70.0\n"
        "chrome,test,3,rail_2,80.0\n")
    records = self._test_merge_browsers(csv_contents)
    score = ((10 + 20) + (30 + 40) + (50 + 60) + (70 + 80)) / 4.0
    self.assertEqual(records, [
        {
            "cb_browser": "chrome",
            "cb_story": "test",
            "odpm_total_mw": score
        },
    ])

  def test_merge_browsers_five_runs_outliers_dropped_ordered(self):
    """Verify that if there are 5 or more runs, the top and bottom totals are
    discarded."""
    csv_contents = (
        "cb_browser,cb_story,cb_run,name,avg_power_mw\n"
        # Run 0
        "chrome,test,0,rail_1,10.0\n"
        "chrome,test,0,rail_2,20.0\n"
        # Run 1
        "chrome,test,1,rail_1,30.0\n"
        "chrome,test,1,rail_2,40.0\n"
        # Run 2
        "chrome,test,2,rail_1,50.0\n"
        "chrome,test,2,rail_2,60.0\n"
        # Run 3
        "chrome,test,3,rail_1,70.0\n"
        "chrome,test,3,rail_2,80.0\n"
        # Run 4
        "chrome,test,4,rail_1,90.0\n"
        "chrome,test,4,rail_2,100.0\n")
    records = self._test_merge_browsers(csv_contents)
    self.assertEqual(records, [
        {
            "cb_browser": "chrome",
            "cb_story": "test",
            "odpm_total_mw": ((20 + 70) + (30 + 80) + (40 + 90)) / 3.0
        },
    ])

  def test_merge_browsers_five_runs_outliers_dropped_unordered(self):
    """Verify that outliers are correctly identified and discarded even when the
    run scores are not chronologically ordered by magnitude."""
    csv_contents = (
        "cb_browser,cb_story,cb_run,name,avg_power_mw\n"
        # Run 0
        "chrome,test,0,rail_1,70.0\n"
        "chrome,test,0,rail_2,80.0\n"
        # Run 1
        "chrome,test,1,rail_1,90.0\n"
        "chrome,test,1,rail_2,100.0\n"
        # Run 2
        "chrome,test,2,rail_1,50.0\n"
        "chrome,test,2,rail_2,60.0\n"
        # Run 3
        "chrome,test,3,rail_1,10.0\n"
        "chrome,test,3,rail_2,20.0\n"
        # Run 4
        "chrome,test,4,rail_1,30.0\n"
        "chrome,test,4,rail_2,40.0\n")
    records = self._test_merge_browsers(csv_contents)
    self.assertEqual(records, [
        {
            "cb_browser": "chrome",
            "cb_story": "test",
            "odpm_total_mw": ((20 + 70) + (30 + 80) + (40 + 90)) / 3.0
        },
    ])

  def test_merge_browsers_many_runs_outliers_dropped_unordered(self):
    """Verify that outliers are discarded for 10 runs. Ensure it's always
    one outlier on the top and one on the bottom, regardless of the number
    of runs."""
    csv_contents = ("cb_browser,cb_story,cb_run,name,avg_power_mw\n"
                    "chrome,test,0,rail,10.0\n"
                    "chrome,test,1,rail,20.0\n"
                    "chrome,test,2,rail,30.0\n"
                    "chrome,test,3,rail,40.0\n"
                    "chrome,test,4,rail,50.0\n"
                    "chrome,test,5,rail,60.0\n"
                    "chrome,test,6,rail,70.0\n"
                    "chrome,test,7,rail,80.0\n"
                    "chrome,test,8,rail,90.0\n"
                    "chrome,test,9,rail,100.0\n")
    records = self._test_merge_browsers(csv_contents)
    self.assertEqual(records, [
        {
            "cb_browser": "chrome",
            "cb_story": "test",
            "odpm_total_mw": (20 + 30 + 40 + 50 + 60 + 70 + 80 + 90) / 8.0
        },
    ])

  def test_merge_browsers_multiple_stories(self):
    """Verify that power metrics are kept isolated per story when
    aggregating."""
    csv_contents = ("cb_browser,cb_story,cb_run,name,avg_power_mw\n"
                    "chrome,cnn,0,rail_1,10.0\n"
                    "chrome,cnn,0,rail_2,20.0\n"
                    "chrome,msn,0,rail_1,5000.0\n"
                    "chrome,msn,0,rail_2,6000.0\n")
    records = self._test_merge_browsers(csv_contents)
    self.assertEqual(records, [
        {
            "cb_browser": "chrome",
            "cb_story": "cnn",
            "odpm_total_mw": 10.0 + 20.0
        },
        {
            "cb_browser": "chrome",
            "cb_story": "msn",
            "odpm_total_mw": 5000.0 + 6000.0
        },
    ])

  def test_merge_browsers_multiple_browsers(self):
    """Verify that power metrics are kept isolated per browser when
    aggregating."""
    csv_contents = ("cb_browser,cb_story,cb_run,name,avg_power_mw\n"
                    "chrome,cnn,0,rail_1,10.0\n"
                    "chrome,cnn,0,rail_2,20.0\n"
                    "safari,cnn,0,rail_1,100.0\n"
                    "safari,cnn,0,rail_2,200.0\n")
    records = self._test_merge_browsers(csv_contents)
    self.assertEqual(records, [
        {
            "cb_browser": "chrome",
            "cb_story": "cnn",
            "odpm_total_mw": 10.0 + 20.0
        },
        {
            "cb_browser": "safari",
            "cb_story": "cnn",
            "odpm_total_mw": 100.0 + 200.0
        },
    ])

  def test_merge_browsers_unsupported_device(self):
    """Verify that a run with only an unsupported/unmapped device results in
    its score being gracefully padded with NaN."""
    csv_contents = "cb_browser,cb_story,cb_run,name,avg_power_mw\n"

    run = mock.MagicMock()
    run.browser.unique_name = "safari"
    run.story.name = "cnn"
    self.group.runs = [run]

    records = self._test_merge_browsers(csv_contents)

    self.assertEqual(records, [
        {
            "cb_browser": "safari",
            "cb_story": "cnn",
            "odpm_total_mw": pytest.approx(float("nan"), nan_ok=True)
        },
    ])

  def test_merge_browsers_multiple_browsers_and_stories(self):
    """Verify that power metrics are kept isolated per browser and story when
    aggregating."""
    csv_contents = ("cb_browser,cb_story,cb_run,name,avg_power_mw\n"
                    "chrome,cnn,0,rail_1,10.0\n"
                    "chrome,cnn,0,rail_2,20.0\n"
                    "safari,cnn,0,rail_1,200.0\n"
                    "safari,cnn,0,rail_2,400.0\n"
                    "chrome,msn,0,rail_1,5000.0\n"
                    "chrome,msn,0,rail_2,6000.0\n")
    records = self._test_merge_browsers(csv_contents)
    self.assertEqual(records, [
        {
            "cb_browser": "chrome",
            "cb_story": "cnn",
            "odpm_total_mw": 10.0 + 20.0
        },
        {
            "cb_browser": "chrome",
            "cb_story": "msn",
            "odpm_total_mw": 5000.0 + 6000.0
        },
        {
            "cb_browser": "safari",
            "cb_story": "cnn",
            "odpm_total_mw": 200.0 + 400.0
        },
    ])

  def test_merge_browsers_multiple_mapped_devices(self):
    """Verify that multiple devices with distinct mappings (e.g. Pixel 9 and
    Pixel 10) are successfully aggregated together if they both output
    power_rails data, while any unsupported devices are padded with NaN."""
    csv_contents = ("cb_browser,cb_story,cb_run,name,avg_power_mw\n"
                    "chrome_pixel_9,test,0,rail_1,10.0\n"
                    "chrome_pixel_9,test,0,rail_2,20.0\n"
                    "chrome_pixel_10,test,0,rail_1,5000.0\n"
                    "chrome_pixel_10,test,0,rail_2,6000.0\n")

    run_p9 = mock.MagicMock()
    run_p9.browser.unique_name = "chrome_pixel_9"
    run_p9.story.name = "test"
    run_p10 = mock.MagicMock()
    run_p10.browser.unique_name = "chrome_pixel_10"
    run_p10.story.name = "test"
    run_safari = mock.MagicMock()
    run_safari.browser.unique_name = "safari"
    run_safari.story.name = "test"
    self.group.runs = [run_p9, run_p10, run_safari]

    records = self._test_merge_browsers(csv_contents)
    self.assertEqual(records, [
        {
            "cb_browser": "chrome_pixel_10",
            "cb_story": "test",
            "odpm_total_mw": 5000.0 + 6000.0
        },
        {
            "cb_browser": "chrome_pixel_9",
            "cb_story": "test",
            "odpm_total_mw": 10.0 + 20.0
        },
        {
            "cb_browser": "safari",
            "cb_story": "test",
            "odpm_total_mw": pytest.approx(float("nan"), nan_ok=True)
        },
    ])

  def test_merge_browsers_missing_trace_result(self):
    """Verify that merge gracefully handles missing trace processor result by
    padding with NaN."""
    result_path = pth.LocalPath("results_dir/web_power_probe")
    self.fs.create_dir(result_path)
    self.group.get_local_probe_result_path.return_value = result_path

    run = mock.MagicMock()
    run.browser.unique_name = "chrome"
    run.story.name = "cnn"
    self.group.runs = [run]

    self.group.results.get_by_name.return_value = None

    result = self.probe.merge_browsers(self.group)

    self.assertEqual(
        self._extract_csv_records(result), [
            {
                "cb_browser": "chrome",
                "cb_story": "cnn",
                "odpm_total_mw": pytest.approx(float("nan"), nan_ok=True)
            },
        ])

  def test_merge_browsers_missing_power_rails(self):
    """Verify that merge gracefully handles missing power rails CSV by padding
    with NaN."""
    result_path = pth.LocalPath("results_dir/web_power_probe")
    self.fs.create_dir(result_path)
    self.group.get_local_probe_result_path.return_value = result_path

    run = mock.MagicMock()
    run.browser.unique_name = "chrome"
    run.story.name = "cnn"
    self.group.runs = [run]

    csv_contents = ("cb_browser,cb_story,cb_run,name,avg_power_mw\n"
                    "chrome,test,0,rail_1,10.0\n"
                    "chrome,test,0,rail_2,20.0\n")

    tp_result = mock.MagicMock()
    # Missing 'power_rails' in filename.
    tp_csv = pth.LocalPath("results_dir/other_query.csv")
    self.fs.create_file(tp_csv, contents=csv_contents)
    tp_result.csv_list = [tp_csv]
    self.group.results.get_by_name.return_value = tp_result

    result = self.probe.merge_browsers(self.group)

    self.assertEqual(
        self._extract_csv_records(result), [
            {
                "cb_browser": "chrome",
                "cb_story": "cnn",
                "odpm_total_mw": pytest.approx(float("nan"), nan_ok=True)
            },
        ])

  def test_merge_browsers_bits_single_run(self):
    self.mock_benchmark.bits_probe = mock.MagicMock()
    csv_file = pth.LocalPath("results_dir/chrome/stories/test/0/0_default/bits/"
                             f"{BitsProbe.BITS_CHANNEL_AVERAGES_CSV_NAME}")
    csv_contents = ("CHANNEL                                 ,       VALUE\n"
                    "BIGCPU:mW                               ,      17.706\n"
                    "MIDCPU:mW                               ,      45.123\n"
                    "CPU:mW                                  ,    1020.796\n"
                    "SOC_TOTAL:mW                            ,    1925.195\n")
    records = self._test_merge_browsers_bits({csv_file: csv_contents})
    self.assertEqual(records, [{
        "cb_browser": "chrome",
        "cb_story": "test",
        "bits_cpu_mw": 1020.796,
        "bits_soc_total_mw": 1925.195,
    }])

  def test_merge_browsers_bits_multiple_runs(self):
    self.mock_benchmark.bits_probe = mock.MagicMock()
    run0_file = pth.LocalPath(
        "results_dir/chrome/stories/test/0/0_default/bits/"
        f"{BitsProbe.BITS_CHANNEL_AVERAGES_CSV_NAME}")
    run0_contents = ("CHANNEL , VALUE\n"
                     "CPU:mW , 100.0\n"
                     "SOC_TOTAL:mW , 500.0\n")
    run1_file = pth.LocalPath(
        "results_dir/chrome/stories/test/1/0_default/bits/"
        f"{BitsProbe.BITS_CHANNEL_AVERAGES_CSV_NAME}")
    run1_contents = ("CHANNEL , VALUE\n"
                     "CPU:mW , 200.0\n"
                     "SOC_TOTAL:mW , 700.0\n")
    records = self._test_merge_browsers_bits({
        run0_file: run0_contents,
        run1_file: run1_contents,
    })
    self.assertEqual(records, [{
        "cb_browser": "chrome",
        "cb_story": "test",
        "bits_cpu_mw": (100.0 + 200.0) / 2.0,
        "bits_soc_total_mw": (500.0 + 700.0) / 2.0,
    }])

  def test_merge_browsers_bits_different_outliers_per_metric(self):
    self.mock_benchmark.bits_probe = mock.MagicMock()
    # 5 runs to trigger outlier removal (>=5 runs).
    # Run 0: Min outlier for CPU (50.0), normal for SOC (500.0).
    # Run 1: Normal for CPU (100.0), Min outlier for SOC (200.0).
    # Run 2: Normal for CPU (110.0), normal for SOC (520.0).
    # Run 3: Normal for CPU (120.0), normal for SOC (540.0).
    # Run 4: Max outlier for CPU (900.0), Max outlier for SOC (1000.0).
    bits_data = {
        0: ("50.0", "500.0"),
        1: ("100.0", "200.0"),
        2: ("110.0", "520.0"),
        3: ("120.0", "540.0"),
        4: ("900.0", "1000.0"),
    }
    files = {
        pth.LocalPath(f"results_dir/chrome/stories/test/{run}/0_default/bits/"
                      f"{BitsProbe.BITS_CHANNEL_AVERAGES_CSV_NAME}"):
            (f"CHANNEL , VALUE\n"
             f"CPU:mW , {cpu}\n"
             f"SOC_TOTAL:mW , {soc}\n") for run, (cpu, soc) in bits_data.items()
    }
    records = self._test_merge_browsers_bits(files)
    # CPU trims 50.0 and 900.0 -> mean(100.0, 110.0, 120.0) = 110.0
    # SOC trims 200.0 and 1000.0 -> mean(500.0, 520.0, 540.0) = 520.0
    self.assertEqual(records, [{
        "cb_browser": "chrome",
        "cb_story": "test",
        "bits_cpu_mw": (100.0 + 110.0 + 120.0) / 3.0,
        "bits_soc_total_mw": (500.0 + 520.0 + 540.0) / 3.0,
    }])

  def test_merge_browsers_bits_and_perfetto(self):
    self.mock_benchmark.bits_probe = mock.MagicMock()
    tp_contents = ("cb_browser,cb_story,cb_run,name,avg_power_mw\n"
                   "chrome,test,0,rail_1,10.0\n"
                   "chrome,test,0,rail_2,20.0\n")
    csv_file = pth.LocalPath("results_dir/chrome/stories/test/0/0_default/bits/"
                             f"{BitsProbe.BITS_CHANNEL_AVERAGES_CSV_NAME}")
    csv_contents = ("CHANNEL , VALUE\n"
                    "CPU:mW , 100.0\n"
                    "SOC_TOTAL:mW , 500.0\n")
    records = self._test_merge_browsers_bits({csv_file: csv_contents},
                                             tp_csv_contents=tp_contents,
                                             metrics=("odpm_total_mw",
                                                      "bits_cpu_mw",
                                                      "bits_soc_total_mw"))
    self.assertEqual(records, [{
        "cb_browser": "chrome",
        "cb_story": "test",
        "odpm_total_mw": 30.0,
        "bits_cpu_mw": 100.0,
        "bits_soc_total_mw": 500.0,
    }])

  def test_merge_browsers_bits_missing_channels(self):
    self.mock_benchmark.bits_probe = mock.MagicMock()
    csv_file = pth.LocalPath("results_dir/chrome/stories/test/0/0_default/bits/"
                             f"{BitsProbe.BITS_CHANNEL_AVERAGES_CSV_NAME}")
    # Verify that substring channels like MIDCPU:mW do NOT match CPU:mW.
    csv_contents = ("CHANNEL , VALUE\n"
                    "BIGCPU:mW , 10.0\n"
                    "MIDCPU:mW , 20.0\n")
    records = self._test_merge_browsers_bits({csv_file: csv_contents})
    self.assertEqual(records, [{
        "cb_browser": "chrome",
        "cb_story": "test",
        "bits_cpu_mw": pytest.approx(float("nan"), nan_ok=True),
        "bits_soc_total_mw": pytest.approx(float("nan"), nan_ok=True),
    }])

  def test_merge_browsers_bits_unsupported_device(self):
    self.mock_benchmark.bits_probe = mock.MagicMock()
    run = mock.MagicMock()
    run.browser.unique_name = "safari"
    run.story.name = "cnn"
    self.group.runs = [run]
    records = self._test_merge_browsers_bits({})
    self.assertEqual(records, [{
        "cb_browser": "safari",
        "cb_story": "cnn",
        "bits_cpu_mw": pytest.approx(float("nan"), nan_ok=True),
        "bits_soc_total_mw": pytest.approx(float("nan"), nan_ok=True),
    }])

  def test_process_result_dir_no_data(self):
    """Verify that process_result_dir handles missing power_rails.csv by
    appending 'No Data' to odpm_total_mw in base_df."""
    base_df = pd.DataFrame([{
        "cb_browser": "chrome",
        "cb_story": "cnn",
    }])
    # In this fake filesystem test, 'results_dir' is never created,
    # ensuring that the underlying 'power_rails.csv' is missing when
    # process_result_dir is called.
    result_dir = pth.LocalPath("results_dir")
    result_df = self.probe.process_result_dir(result_dir, base_df)
    self.assertEqual(len(result_df), 1)
    self.assertEqual(result_df["cb_browser"].iloc[0], "chrome")
    self.assertEqual(result_df["odpm_total_mw"].iloc[0], "No Data")

  def test_process_result_dir_from_csv(self):
    """Verify that process_result_dir can read data from a pre-existing CSV."""
    base_df = pd.DataFrame([{
        "cb_browser": "chrome",
        "cb_story": "cnn",
    }])
    result_dir = pth.LocalPath("results_dir")
    csv_path = result_dir / "trace_processor" / "power_rails.csv"
    self.fs.create_file(
        csv_path,
        contents="cb_browser,cb_story,cb_run,name,avg_power_mw\n"
        "chrome,cnn,0,rail_1,10.0\n"
        "chrome,cnn,0,rail_2,20.0\n")

    result_df = self.probe.process_result_dir(
        result_dir, base_df, reprocess=False)
    self.assertEqual(len(result_df), 1)
    self.assertEqual(result_df["cb_browser"].iloc[0], "chrome")
    self.assertEqual(result_df["odpm_total_mw"].iloc[0], 30.0)

  @mock.patch("crossbench.benchmarks.web_power.probe.BatchTraceProcessor")
  def test_process_result_dir_reprocess(self, btp_mock):
    """Verify that process_result_dir ignores existing CSVs and reruns traces
    when reprocess=True.
    """
    base_df = pd.DataFrame([{
        "cb_browser": "chrome",
        "cb_story": "cnn",
        "device_model": "test_device",
    }])
    result_dir = pth.LocalPath("results_dir")

    # Create an old CSV that should be ignored and overwritten.
    csv_path = result_dir / "trace_processor" / "power_rails.csv"
    self.fs.create_file(
        csv_path,
        contents="cb_browser,cb_story,cb_run,name,avg_power_mw\n"
        "chrome,cnn,0,rail_1,999.0\n")

    # Create a trace file so it triggers reprocess.
    trace_file = (
        result_dir / "chrome" / "stories" / "cnn" / "0" / "0_default" /
        "trace.pb.gz")
    self.fs.create_file(trace_file)

    # Create the fallback SQL file so that process_result_dir actually
    # executes the query.
    sql_file = QUERIES_DIR / "web_power" / "power_rails.sql"
    self.fs.create_file(sql_file, contents="SELECT 1")
    mapping_file = QUERIES_DIR / "web_power" / "mapping.hjson"
    self.fs.create_file(
        mapping_file, contents='{".*": "web_power/power_rails"}')

    btp_instance = btp_mock.return_value.__enter__.return_value
    btp_instance.query_and_flatten.return_value = pd.DataFrame({
        "_path": [str(trace_file)],
        "name": ["rail_1"],
        "avg_power_mw": [50.0],
    })

    result_df = self.probe.process_result_dir(
        result_dir, base_df, reprocess=True)
    self.assertEqual(len(result_df), 1)
    self.assertEqual(result_df["cb_browser"].iloc[0], "chrome")
    # Should be 50.0 from the mock BTP, not 999.0 from the CSV.
    self.assertEqual(result_df["odpm_total_mw"].iloc[0], 50.0)
    btp_mock.assert_called_once_with(traces=[str(trace_file)], config=mock.ANY)
    btp_instance.query_and_flatten.assert_called_once_with("SELECT 1")

  def test_process_result_dir_preserves_column_order(self):
    """Verify that process_result_dir preserves the exact column order of the
    base_df, appending any newly computed metrics to the end."""
    base_df = pd.DataFrame([{
        "custom_first_col": "foo",
        "cb_browser": "chrome",
        "cb_story": "cnn",
        "custom_middle_col": "bar",
    }])
    result_dir = pth.LocalPath("results_dir")

    # Create a minimal CSV so it falls back to reading it (reprocess=False)
    csv_path = result_dir / "trace_processor" / "power_rails.csv"
    self.fs.create_file(
        csv_path,
        contents="cb_browser,cb_story,cb_run,name,avg_power_mw\n"
        "chrome,cnn,0,rail_1,10.0\n")

    result_df = self.probe.process_result_dir(
        result_dir, base_df, reprocess=False)

    expected_cols = [
        "custom_first_col", "cb_browser", "cb_story", "custom_middle_col",
        "odpm_total_mw"
    ]
    self.assertListEqual(list(result_df.columns), expected_cols)

  def test_merge_browsers_multiple_power_rails(self):
    """Verify that merge fails if multiple power rails CSVs are found,
    indicating an ambiguous query mapping."""
    result_path = pth.LocalPath("results_dir/web_power_probe")
    self.group.get_local_probe_result_path.return_value = result_path

    csv_contents = ("cb_browser,cb_story,cb_run,name,avg_power_mw\n"
                    "chrome,test,0,rail_1,10.0\n")

    tp_result = mock.MagicMock()
    tp_csv_1 = pth.LocalPath("results_dir/power_rails.csv")
    tp_csv_2 = pth.LocalPath("results_dir/other_power_rails.csv")
    self.fs.create_file(tp_csv_1, contents=csv_contents)
    self.fs.create_file(tp_csv_2, contents=csv_contents)

    tp_result.csv_list = [tp_csv_1, tp_csv_2]
    self.group.results.get_by_name.return_value = tp_result

    with self.assertRaisesRegex(ProbeMissingDataError,
                                "Multiple power_rails results found"):
      self.probe.merge_browsers(self.group)

  def _test_get_extra_probes(
      self, has_probe_side_effect: Callable[[str], bool]) -> tuple[Probe, ...]:
    """Helper to verify get_extra_probes behavior with a mocked has_probe.

    It creates a minimal mock mapping.hjson file in the fake filesystem
    so that it does not crash when attempting to load the device-specific
    query mapping, sets up the has_probe side-effect on the runner,
    and returns the resolved extra probes.
    """
    mapping_dir = QUERIES_DIR / "web_power"
    self.fs.create_dir(mapping_dir)
    self.fs.create_file(mapping_dir / "mapping.hjson", contents="{}")
    self.runner.has_probe.side_effect = has_probe_side_effect
    return tuple(self.probe.get_extra_probes(self.runner))

  def test_get_extra_probes_with_perfetto(self):
    extra_probes = self._test_get_extra_probes(lambda name: name == "perfetto")
    probe_names = tuple(p.name for p in extra_probes)
    self.assertEqual(probe_names, ("trace_processor",))

  def test_get_extra_probes_without_perfetto(self):
    extra_probes = self._test_get_extra_probes(lambda name: False)
    self.assertEqual(extra_probes, ())

  def test_get_extra_probes_with_bits(self):
    bits_probe = mock.MagicMock(spec=BitsProbe, name="bits")
    self.mock_benchmark.bits_probe = bits_probe
    extra_probes = self._test_get_extra_probes(lambda name: False)
    self.assertEqual(extra_probes, (bits_probe,))

  def test_get_extra_probes_with_bits_and_perfetto(self):
    bits_probe = mock.MagicMock(spec=BitsProbe, name="bits")
    self.mock_benchmark.bits_probe = bits_probe
    extra_probes = self._test_get_extra_probes(lambda name: name == "perfetto")
    self.assertEqual(len(extra_probes), 2)
    self.assertEqual(extra_probes[0], bits_probe)
    self.assertEqual(extra_probes[1].name, "trace_processor")


class Mapping(enum.Enum):
  PUBLIC = "public"
  INTERNAL = "internal"


class WebPowerProbeMappingTestCase(CrossbenchFakeFsTestCase):
  """Verifies how the probe handles edge cases (e.g., missing directories,
  invalid JSON, broken regexes, missing SQL files). We check this independently
  of whether the repository actually has the internal Crossbench module, so
  that users with the internal repo won't break things for those without,
  and vice versa.
  """

  def setUp(self):
    super().setUp()
    self.mock_benchmark = mock.MagicMock(bits_probe=None)
    self.mock_benchmark.version.return_value = tuple(
        map(int, VERSION_STRING.split(".")))
    self.probe = WebPowerProbe(benchmark=self.mock_benchmark)
    self.runner = mock.MagicMock()
    # Simulate that only the "perfetto" probe is attached.
    self.runner.has_probe.side_effect = lambda name: name == "perfetto"

  def _get_mapping_dir(self, mapping: Mapping) -> pth.LocalPath:
    match mapping:
      case Mapping.PUBLIC:
        return QUERIES_DIR / "web_power"
      case Mapping.INTERNAL:
        return WebPowerProbe.INTERNAL_QUERIES_DIR
      case _:
        raise ValueError(f"Unknown mapping: {mapping}")

  def _create_mapping_dir(self, mapping: Mapping):
    self.fs.create_dir(self._get_mapping_dir(mapping))

  def _create_mapping_file(self, mapping: Mapping, contents: str = "{}"):
    self.fs.create_file(
        self._get_mapping_dir(mapping) / "mapping.hjson", contents=contents)

  def _setup_mapping(self,
                     public_contents: str = "{}",
                     internal_contents: str = "{}"):
    self._create_mapping_dir(Mapping.PUBLIC)
    self._create_mapping_file(Mapping.PUBLIC, contents=public_contents)
    self._create_mapping_dir(Mapping.INTERNAL)
    self._create_mapping_file(Mapping.INTERNAL, contents=internal_contents)

  def _create_sql_file(self,
                       mapping: Mapping,
                       name: str,
                       contents: str = "SELECT 1") -> pth.LocalPath:
    match mapping:
      case Mapping.PUBLIC:
        path = self._get_mapping_dir(mapping) / name
      case Mapping.INTERNAL:
        path = self._get_mapping_dir(mapping).parent / name
      case _:
        raise ValueError(f"Unknown mapping: {mapping}")
    self.fs.create_file(path, contents=contents)
    return path

  def test_load_mapping_missing_public_mapping_dir(self):
    """Verify that get_extra_probes fails if public mapping dir is missing."""
    self._create_mapping_dir(Mapping.INTERNAL)
    self._create_mapping_file(Mapping.INTERNAL)
    # Explicitly NOT calling self._create_mapping_dir(Mapping.PUBLIC)
    # Explicitly NOT calling self._create_mapping_file(Mapping.PUBLIC)
    with self.assertRaisesRegex(
        ValueError, "Mapping file does not exist: " +
        re.escape(str(QUERIES_DIR / "web_power/mapping.hjson"))):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_missing_public_mapping_file(self):
    """Verify that get_extra_probes fails if public mapping.hjson is missing."""
    self._create_mapping_dir(Mapping.PUBLIC)
    self._create_mapping_dir(Mapping.INTERNAL)
    self._create_mapping_file(Mapping.INTERNAL)
    # Explicitly NOT calling self._create_mapping_file(Mapping.PUBLIC)
    with self.assertRaisesRegex(
        ValueError, "Mapping file does not exist: " +
        re.escape(str(QUERIES_DIR / "web_power/mapping.hjson"))):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_missing_internal_mapping_expected(self):
    """Verify failure if internal dir exists but lacks mapping.hjson."""
    self._create_mapping_dir(Mapping.PUBLIC)
    self._create_mapping_file(Mapping.PUBLIC)
    self._create_mapping_dir(Mapping.INTERNAL)
    # Explicitly NOT calling self._create_mapping_file(Mapping.INTERNAL)
    with self.assertRaisesRegex(
        ValueError, "Mapping file does not exist: " +
        re.escape(str(WebPowerProbe.INTERNAL_QUERIES_DIR / "mapping.hjson"))):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_missing_internal_mapping_not_expected(self):
    """Verify success if internal dir doesn't exist (mapping not expected)."""
    self._create_mapping_dir(Mapping.PUBLIC)
    self._create_mapping_file(Mapping.PUBLIC)
    # Explicitly NOT calling self._create_mapping_dir(Mapping.INTERNAL)
    # Should not raise any error.
    self.probe.get_extra_probes(self.runner)

  def test_load_mapping_both_valid_json(self):
    """Verify get_extra_probes succeeds with empty valid mapping.hjson files."""
    self._setup_mapping(public_contents="{}", internal_contents="{}")
    # Should not raise any error.
    self.probe.get_extra_probes(self.runner)

  def test_load_mapping_invalid_json_public(self):
    """Verify that get_extra_probes raises an error when public mapping.hjson
    is invalid JSON."""
    self._setup_mapping(public_contents="{ invalid json")
    with self.assertRaises(argparse.ArgumentTypeError):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_invalid_json_internal(self):
    """Verify that get_extra_probes raises an error when internal mapping.hjson
    is invalid JSON."""
    self._setup_mapping(internal_contents="{ invalid json")
    with self.assertRaises(argparse.ArgumentTypeError):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_invalid_regex_both(self):
    """Verify that an invalid regex in both mapping.hjson files raises an
    error."""
    self._setup_mapping(
        public_contents='{"[": "web_power/public_valid_sql"}',
        internal_contents='{"[": "internal_valid_sql"}')
    self._create_sql_file(Mapping.PUBLIC, "public_valid_sql.sql")
    self._create_sql_file(Mapping.INTERNAL, "internal_valid_sql.sql")
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "Invalid regexp"):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_invalid_regex_public(self):
    """Verify that an invalid regex in public mapping.hjson raises an error."""
    self._setup_mapping(public_contents='{"[": "web_power/public_valid_sql"}')
    self._create_sql_file(Mapping.PUBLIC, "public_valid_sql.sql")
    self._create_sql_file(Mapping.INTERNAL, "internal_valid_sql.sql")
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "Invalid regexp"):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_invalid_regex_internal(self):
    """Verify that an invalid regex in internal mapping.hjson raises an
    error."""
    self._setup_mapping(internal_contents='{"[": "internal_valid_sql"}')
    self._create_sql_file(Mapping.PUBLIC, "public_valid_sql.sql")
    self._create_sql_file(Mapping.INTERNAL, "internal_valid_sql.sql")
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "Invalid regexp"):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_missing_sql_file_public(self):
    """Verify that a missing SQL file mapped in public mapping.hjson raises
    an error."""
    self._setup_mapping(public_contents='{"Device A": "web_power/missing_sql"}')
    with self.assertRaisesRegex(argparse.ArgumentTypeError,
                                "Mapped SQL file path does not exist"):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_missing_sql_file_internal(self):
    """Verify that a missing SQL file mapped in internal mapping.hjson raises
    an error."""
    self._setup_mapping(
        internal_contents='{"Device A": "internal_missing_sql"}')
    with self.assertRaisesRegex(argparse.ArgumentTypeError,
                                "Mapped SQL file path does not exist"):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_success(self):
    """Verify that get_extra_probes succeeds when mappings are valid."""
    self._setup_mapping(
        public_contents='{"Public Device": "web_power/public_query"}',
        internal_contents='{"Internal Device": "internal_query"}')
    public_sql = self._create_sql_file(Mapping.PUBLIC, "public_query.sql")
    internal_sql = self._create_sql_file(Mapping.INTERNAL, "internal_query.sql")

    (tp_probe,) = self.probe.get_extra_probes(self.runner)
    (query,) = tp_probe.queries

    self.assertDictEqual(
        dict(query.device_override), {
            re.compile("Public Device"): str(public_sql.resolve()),
            re.compile("Internal Device"): str(internal_sql.resolve()),
        })


class WebPowerProbeRealFsTestCase(unittest.TestCase):
  """Validates the actual mapping files committed to the repository.
  This unlike WebPowerProbeMappingTestCase, which checked what the code
  would do with/without the dirs and files."""

  def _test_real_mapping_dir(self, directory: pth.LocalPath,
                             require_mappings: bool):
    probe = WebPowerProbe(benchmark=mock.MagicMock())
    mapping = probe._load_mapping(directory)
    self.assertIsInstance(mapping, dict)
    if require_mappings:
      self.assertGreater(len(mapping), 0)

  def test_load_mapping_public_repo_valid(self):
    """Verify that the public QUERIES_DIR mapping.hjson parses correctly."""
    self._test_real_mapping_dir(
        QUERIES_DIR / "web_power", require_mappings=True)

  @unittest.skipIf(not WebPowerProbe.INTERNAL_QUERIES_DIR.is_dir(),
                   "Internal queries directory does not exist.")
  def test_load_mapping_internal_repo_valid(self):
    """Verify that the internal mapping.hjson (if present) parses correctly."""
    self._test_real_mapping_dir(
        WebPowerProbe.INTERNAL_QUERIES_DIR, require_mappings=False)


class WebPowerProbeQueryValidationTestCase(unittest.TestCase):
  """Tests validating the SQL queries used by WebPowerProbe."""

  def setUp(self):
    super().setUp()

    # Initialize the WebPowerProbe and extract its underlying
    # TraceProcessorProbe and SQL query configuration for validation testing.
    self.probe = WebPowerProbe(benchmark=mock.MagicMock(bits_probe=None))
    self.runner = mock.MagicMock(has_probe=lambda name: name == "perfetto")
    extra_probes = tuple(self.probe.get_extra_probes(self.runner))
    self.assertEqual(len(extra_probes), 1)
    self.tp_probe = extra_probes[0]
    self.assertIsInstance(self.tp_probe, TraceProcessorProbe)
    self.tp_probe._browsers.clear()
    self.assertEqual(len(self.tp_probe.queries), 1)
    self.query = self.tp_probe.queries[0]
    self.assertIsInstance(self.query, DeviceSpecificTraceProcessorQuery)

    self._setup_dummy_browsers()

  def _setup_dummy_browsers(self):
    """
    Overwrite the regex keys in the original device overrides with simple
    dummy device names ('0', '1', ...) and create corresponding mock browsers.
    This ensures that every mapped SQL file is validated exactly once
    without presupposing the structure of the original regex mappings.
    """

    paths = list(self.query.device_override.values())
    dummy_overrides: dict[str, str] = {}

    for path in paths:
      device_name = str(len(self.tp_probe.browsers))
      dummy_overrides[device_name] = path
      browser = mock.MagicMock()
      browser.platform.model = device_name
      self.tp_probe.attach(browser)

    self.query = DeviceSpecificTraceProcessorQuery.create(
        name=self.query.name, device_override=dummy_overrides)
    self.tp_probe._queries = (self.query,)

  def _run_validation_with_sql(self, sql_content: str, device_name: str):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql") as sql_file:
      sql_file.write(sql_content)
      sql_file.flush()

      overrides = {device_name: sql_file.name}
      test_query = DeviceSpecificTraceProcessorQuery.create(
          name=self.query.name, device_override=overrides)
      self.tp_probe._queries = (test_query,)
      browser = mock.MagicMock()
      browser.platform.model = device_name
      self.tp_probe.attach(browser)

      self.tp_probe.validate_env(mock.MagicMock())

  def test_valid_query_passes_validation(self):
    """Verify that our validation mechanism successfully accepts valid SQL
    queries."""
    self._run_validation_with_sql("SELECT 1;", "valid_device")

  def test_defective_query_fails_validation(self):
    """Verify that our validation mechanism correctly detects and fails on
    invalid SQL syntax."""
    with self.assertRaises(MultiException) as cm:
      self._run_validation_with_sql("SYNTAX ERROR;", "defective_device")
    self.assertIn("syntax error", str(cm.exception))

  def test_queries_are_valid_and_compile(self):
    """Verify that the actual production SQL queries in WebPowerProbe are valid
    and compile correctly."""
    self.tp_probe.validate_env(mock.MagicMock())


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
