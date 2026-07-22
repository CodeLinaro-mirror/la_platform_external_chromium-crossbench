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
    self.mock_benchmark = mock.MagicMock()
    self.mock_benchmark.version.return_value = tuple(
        map(int, VERSION_STRING.split(".")))
    self.probe = WebPowerProbe(benchmark=self.mock_benchmark)
    self.group = mock.MagicMock()
    self.group.results = mock.MagicMock()
    self.runner = mock.MagicMock()
    # Simulate that only the "perfetto" probe is attached.
    self.runner.has_probe.side_effect = lambda name: name == "perfetto"

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
    tp_csv = pth.LocalPath("results_dir/trace_processor/power_rails.csv")
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

  def test_process_result_dir_no_data(self):
    """Verify that process_result_dir handles missing power_rails.csv by
    appending 'No Data' to total_power_mw in base_df."""
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
    self.assertEqual(result_df["total_power_mw"].iloc[0], "No Data")

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
    self.probe = WebPowerProbe(benchmark=mock.MagicMock())
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

    paths = list(self.query._device_override.values())
    self.query._device_override.clear()

    for path in paths:
      device_name = str(len(self.tp_probe.browsers))
      self.query._device_override[re.compile(device_name)] = path
      browser = mock.MagicMock()
      browser.platform.model = device_name
      self.tp_probe.attach(browser)

  def _run_validation_with_sql(self, sql_content: str, device_name: str):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql") as sql_file:
      sql_file.write(sql_content)
      sql_file.flush()

      self.query._device_override[re.compile(device_name)] = sql_file.name
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
