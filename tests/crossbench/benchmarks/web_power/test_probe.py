# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import typing
from unittest import mock

import pandas as pd
import pytest

from crossbench import path as pth
from crossbench.benchmarks.web_power.base import VERSION_STRING
from crossbench.benchmarks.web_power.probe import WebPowerProbe
from crossbench.probes.probe_context import EmptyProbeContext
from crossbench.probes.probe_error import ProbeMissingDataError
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


class WebPowerProbeTestCase(CrossbenchFakeFsTestCase):

  def setUp(self):
    super().setUp()
    self.mock_benchmark = mock.MagicMock()
    self.mock_benchmark.version.return_value = tuple(
        map(int, VERSION_STRING.split(".")))
    self.probe = WebPowerProbe(benchmark=self.mock_benchmark)
    self.group = mock.MagicMock()
    self.group.results = mock.MagicMock()

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
    critical_mock.assert_called()

  def _test_merge_browsers(self, csv_contents: str) -> list[dict]:
    result_path = pth.LocalPath("results_dir/web_power_probe")
    self.group.get_local_probe_result_path.return_value = result_path

    tp_result = mock.MagicMock()
    tp_csv = pth.LocalPath("results_dir/power_rails.csv")
    self.fs.create_file(tp_csv, contents=csv_contents)
    tp_result.csv_list = [tp_csv]
    self.group.results.get_by_name.return_value = tp_result

    result = self.probe.merge_browsers(self.group)

    self.assertTrue(result.csv)
    out_csv = result.csv
    self.assertEqual(out_csv, pth.LocalPath("results_dir/power_scores.csv"))

    df = pd.read_csv(out_csv)
    df = df.sort_values(by=["cb_browser", "cb_story"]).reset_index(drop=True)
    return df.to_dict(orient="records")

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
            "total_power_mw": 10.0 + 20.0
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
            "total_power_mw": ((10.0 + 20.0) + (200.0 + 400.0)) / 2.0
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
            "total_power_mw": 10.0 + 20.0
        },
        {
            "cb_browser": "chrome",
            "cb_story": "msn",
            "total_power_mw": 5000.0 + 6000.0
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
            "total_power_mw": 10.0 + 20.0
        },
        {
            "cb_browser": "safari",
            "cb_story": "cnn",
            "total_power_mw": 100.0 + 200.0
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
            "total_power_mw": pytest.approx(float("nan"), nan_ok=True)
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
            "total_power_mw": 10.0 + 20.0
        },
        {
            "cb_browser": "chrome",
            "cb_story": "msn",
            "total_power_mw": 5000.0 + 6000.0
        },
        {
            "cb_browser": "safari",
            "cb_story": "cnn",
            "total_power_mw": 200.0 + 400.0
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
            "total_power_mw": 5000.0 + 6000.0
        },
        {
            "cb_browser": "chrome_pixel_9",
            "cb_story": "test",
            "total_power_mw": 10.0 + 20.0
        },
        {
            "cb_browser": "safari",
            "cb_story": "test",
            "total_power_mw": pytest.approx(float("nan"), nan_ok=True)
        },
    ])

  def test_merge_browsers_missing_trace_result(self):
    """Verify that merge fails if the TraceProcessorProbe results are
    completely missing."""
    result_path = pth.LocalPath("results_dir/web_power_probe")
    self.group.get_local_probe_result_path.return_value = result_path

    self.group.results.get_by_name.return_value = None

    with self.assertRaisesRegex(ProbeMissingDataError,
                                "has no TraceProcessorProbe result"):
      self.probe.merge_browsers(self.group)

  def test_merge_browsers_missing_power_rails(self):
    """Verify that merge fails if the TraceProcessorProbe results exist but
    lack the specific power rails CSV."""
    result_path = pth.LocalPath("results_dir/web_power_probe")
    self.group.get_local_probe_result_path.return_value = result_path

    csv_contents = ("cb_browser,cb_story,cb_run,name,avg_power_mw\n"
                    "chrome,test,0,rail_1,10.0\n"
                    "chrome,test,0,rail_2,20.0\n")

    tp_result = mock.MagicMock()
    # Missing 'power_rails' in filename.
    tp_csv = pth.LocalPath("results_dir/other_query.csv")
    self.fs.create_file(tp_csv, contents=csv_contents)
    tp_result.csv_list = [tp_csv]
    self.group.results.get_by_name.return_value = tp_result

    with self.assertRaisesRegex(ProbeMissingDataError,
                                "power_rails result not found"):
      self.probe.merge_browsers(self.group)

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


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
