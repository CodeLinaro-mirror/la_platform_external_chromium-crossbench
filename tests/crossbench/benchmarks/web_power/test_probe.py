# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import enum
import json
import re
import typing
import unittest
from unittest import mock

import pandas as pd
import pytest

from crossbench import path as pth
from crossbench.benchmarks.web_power.base import VERSION_STRING
from crossbench.benchmarks.web_power.probe import WebPowerProbe
from crossbench.probes.probe_context import EmptyProbeContext
from crossbench.probes.probe_error import ProbeMissingDataError
from crossbench.probes.trace_processor.constants import QUERIES_DIR
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
    self.runner = mock.MagicMock()
    self.runner.has_probe.return_value = False

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

  def _extract_csv_records(self, result):
    self.assertTrue(result.csv)
    df = pd.read_csv(result.csv)
    return df.to_dict(orient="records")

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
                "total_power_mw": pytest.approx(float("nan"), nan_ok=True)
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
                "total_power_mw": pytest.approx(float("nan"), nan_ok=True)
            },
        ])

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
    self.mock_benchmark = mock.MagicMock()
    self.mock_benchmark.version.return_value = tuple(
        map(int, VERSION_STRING.split(".")))
    self.probe = WebPowerProbe(benchmark=self.mock_benchmark)
    self.runner = mock.MagicMock()
    self.runner.has_probe.return_value = False

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
        self._get_mapping_dir(mapping) / "mapping.json", contents=contents)

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
        re.escape(str(QUERIES_DIR / "web_power/mapping.json"))):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_missing_public_mapping_file(self):
    """Verify that get_extra_probes fails if public mapping.json is missing."""
    self._create_mapping_dir(Mapping.PUBLIC)
    self._create_mapping_dir(Mapping.INTERNAL)
    self._create_mapping_file(Mapping.INTERNAL)
    # Explicitly NOT calling self._create_mapping_file(Mapping.PUBLIC)
    with self.assertRaisesRegex(
        ValueError, "Mapping file does not exist: " +
        re.escape(str(QUERIES_DIR / "web_power/mapping.json"))):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_missing_internal_mapping_expected(self):
    """Verify failure if internal dir exists but lacks mapping.json."""
    self._create_mapping_dir(Mapping.PUBLIC)
    self._create_mapping_file(Mapping.PUBLIC)
    self._create_mapping_dir(Mapping.INTERNAL)
    # Explicitly NOT calling self._create_mapping_file(Mapping.INTERNAL)
    with self.assertRaisesRegex(
        ValueError, "Mapping file does not exist: " +
        re.escape(str(WebPowerProbe.INTERNAL_QUERIES_DIR / "mapping.json"))):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_missing_internal_mapping_not_expected(self):
    """Verify success if internal dir doesn't exist (mapping not expected)."""
    self._create_mapping_dir(Mapping.PUBLIC)
    self._create_mapping_file(Mapping.PUBLIC)
    # Explicitly NOT calling self._create_mapping_dir(Mapping.INTERNAL)
    # Should not raise any error.
    self.probe.get_extra_probes(self.runner)

  def test_load_mapping_both_valid_json(self):
    """Verify get_extra_probes succeeds with empty valid mapping.json files."""
    self._setup_mapping(public_contents="{}", internal_contents="{}")
    # Should not raise any error.
    self.probe.get_extra_probes(self.runner)

  def test_load_mapping_invalid_json_public(self):
    """Verify that get_extra_probes raises an error when public mapping.json
    is invalid JSON."""
    self._setup_mapping(public_contents="{ invalid json")
    with self.assertRaises(json.JSONDecodeError):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_invalid_json_internal(self):
    """Verify that get_extra_probes raises an error when internal mapping.json
    is invalid JSON."""
    self._setup_mapping(internal_contents="{ invalid json")
    with self.assertRaises(json.JSONDecodeError):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_invalid_regex_both(self):
    """Verify that an invalid regex in both mapping.json files raises an
    error."""
    self._setup_mapping(
        public_contents='{"[": "web_power/public_valid_sql"}',
        internal_contents='{"[": "internal_valid_sql"}')
    self._create_sql_file(Mapping.PUBLIC, "public_valid_sql.sql")
    self._create_sql_file(Mapping.INTERNAL, "internal_valid_sql.sql")
    with self.assertRaisesRegex(ValueError, "Invalid regex in mapping key"):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_invalid_regex_public(self):
    """Verify that an invalid regex in public mapping.json raises an error."""
    self._setup_mapping(public_contents='{"[": "web_power/public_valid_sql"}')
    self._create_sql_file(Mapping.PUBLIC, "public_valid_sql.sql")
    self._create_sql_file(Mapping.INTERNAL, "internal_valid_sql.sql")
    with self.assertRaisesRegex(ValueError, "Invalid regex in mapping key"):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_invalid_regex_internal(self):
    """Verify that an invalid regex in internal mapping.json raises an error."""
    self._setup_mapping(internal_contents='{"[": "internal_valid_sql"}')
    self._create_sql_file(Mapping.PUBLIC, "public_valid_sql.sql")
    self._create_sql_file(Mapping.INTERNAL, "internal_valid_sql.sql")
    with self.assertRaisesRegex(ValueError, "Invalid regex in mapping key"):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_missing_sql_file_public(self):
    """Verify that a missing SQL file mapped in public mapping.json raises
    an error."""
    self._setup_mapping(public_contents='{"Device A": "web_power/missing_sql"}')
    with self.assertRaisesRegex(ValueError, "Mapped SQL file does not exist"):
      self.probe.get_extra_probes(self.runner)

  def test_load_mapping_missing_sql_file_internal(self):
    """Verify that a missing SQL file mapped in internal mapping.json raises
    an error."""
    self._setup_mapping(
        internal_contents='{"Device A": "internal_missing_sql"}')
    with self.assertRaisesRegex(ValueError, "Mapped SQL file does not exist"):
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
        query._device_override, {
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
    """Verify that the public QUERIES_DIR mapping.json parses correctly."""
    self._test_real_mapping_dir(
        QUERIES_DIR / "web_power", require_mappings=True)

  @unittest.skipIf(not WebPowerProbe.INTERNAL_QUERIES_DIR.is_dir(),
                   "Internal queries directory does not exist.")
  def test_load_mapping_internal_repo_valid(self):
    """Verify that the internal mapping.json (if present) parses correctly."""
    self._test_real_mapping_dir(
        WebPowerProbe.INTERNAL_QUERIES_DIR, require_mappings=False)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
