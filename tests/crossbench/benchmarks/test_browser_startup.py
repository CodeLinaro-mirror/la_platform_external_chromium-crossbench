# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Sequence
from unittest import mock

import pandas as pd

from crossbench import path as pth
from crossbench.action_runner.action.enums import ReadyState
from crossbench.action_runner.action.start_browser import StartBrowserAction
from crossbench.action_runner.action.wait_for_condition import \
    WaitForConditionAction
from crossbench.action_runner.action.wait_for_ready_state import \
    WaitForReadyStateAction
from crossbench.action_runner.action.wait_for_url_matches import \
    WaitForUrlMatchesAction
from crossbench.benchmarks.loading.browser_startup import \
    BrowserStartupBenchmark, BrowserStartupProbe
from crossbench.benchmarks.loading.config.pages import PagesConfig
from crossbench.benchmarks.loading.page.interactive import InteractivePage
from crossbench.browsers.splash_screen import SplashScreen
from crossbench.cli.parser import CBArgumentParser
from crossbench.cli.subcommand.benchmark import BenchmarkSubcommand
from crossbench.probes.results import LocalProbeResult, ProbeResultDict
from crossbench.probes.trace_processor.trace_processor import \
    TraceProcessorProbe
from tests import test_helper
from tests.crossbench.base import BaseCliTestCase, BaseCrossbenchTestCase
from tests.crossbench.mock_helper import MockCLI


class TestBrowserStartupBenchmark(BaseCrossbenchTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.setup_config_dir(
        BrowserStartupBenchmark.default_probe_config_path().parent)

  def parse_args(self, *args: str | Sequence[str]) -> argparse.Namespace:
    parser = BrowserStartupBenchmark.add_cli_arguments(CBArgumentParser())
    flattened_args: list[str] = []
    for arg in args:
      if isinstance(arg, str):
        flattened_args.append(arg)
      else:
        flattened_args.extend(arg)
    return parser.parse_args(flattened_args)

  def test_describe(self) -> None:
    desc = BrowserStartupBenchmark.describe()
    self.assertEqual(desc["name"], "browser-startup")
    self.assertEqual(desc["aliases"], "None")
    self.assertTrue(len(desc["description"]) > 0)
    self.assertEqual(
        desc["stories"],
        {
            "newtab_startup": "chrome://newtab/",
            "blank_startup": "about:blank",
            "google_startup": "https://www.google.com/",
        })
    probes_default = desc.get("probes_default") or desc.get("probes-default")
    self.assertIsInstance(probes_default, dict)
    self.assertIn("browser_startup", probes_default)

  def test_all_story_names(self) -> None:
    self.assertSequenceEqual(
        BrowserStartupBenchmark.all_story_names(),
        ("newtab_startup", "blank_startup", "google_startup"))

  def test_properties(self) -> None:
    self.assertEqual(BrowserStartupBenchmark.NAME, "browser-startup")
    self.assertEqual(BrowserStartupBenchmark.DEFAULT_SPLASH_SCREEN,
                     SplashScreen.NONE)
    self.assertFalse(BrowserStartupBenchmark.DEFAULT_START_BROWSER)
    self.assertSequenceEqual(BrowserStartupBenchmark.aliases(), ())
    self.assertSequenceEqual(
        BrowserStartupBenchmark.PROBES, (BrowserStartupProbe,))
    self.assertTrue(
        BrowserStartupBenchmark.default_probe_config_path().is_file())
    self.assertTrue(
        BrowserStartupBenchmark.default_pages_config_path().is_file())

  def test_get_pages_config(self) -> None:
    config = BrowserStartupBenchmark.get_pages_config()
    self.assertIsInstance(config, PagesConfig)
    self.assertEqual(len(config.pages), 3)
    page_labels = [page.label for page in config.pages]
    self.assertSequenceEqual(
        page_labels, ["newtab_startup", "blank_startup", "google_startup"])
    expected_stories = (
        ("chrome://newtab/", "^chrome://"),
        ("about:blank", None),
        ("https://www.google.com/", "^https://"),
    )
    for page, (expected_url, expected_pattern) in zip(
        config.pages, expected_stories, strict=True):
      actions = tuple(page.actions())
      start_action = actions[0]
      self.assertIsInstance(start_action, StartBrowserAction)
      assert isinstance(start_action, StartBrowserAction)
      self.assertEqual(start_action.startup_urls, (expected_url,))
      if expected_pattern is None:
        self.assertEqual(len(actions), 3)
        ready_action, paint_wait_action = actions[1:]
      else:
        self.assertEqual(len(actions), 4)
        url_wait_action, ready_action, paint_wait_action = actions[1:]
        self.assertIsInstance(url_wait_action, WaitForUrlMatchesAction)
        assert isinstance(url_wait_action, WaitForUrlMatchesAction)
        self.assertEqual(url_wait_action.url_pattern.pattern,
                         expected_pattern)
      self.assertIsInstance(ready_action, WaitForReadyStateAction)
      assert isinstance(ready_action, WaitForReadyStateAction)
      self.assertEqual(ready_action.ready_state, ReadyState.COMPLETE)
      self.assertIsInstance(paint_wait_action, WaitForConditionAction)
      assert isinstance(paint_wait_action, WaitForConditionAction)
      self.assertIn("requestAnimationFrame", paint_wait_action.condition)

  def test_separate_stories_by_default(self) -> None:
    args = self.parse_args()
    self.assertTrue(args.separate)
    benchmark = BrowserStartupBenchmark.from_cli_args(args)
    self.assertEqual(len(benchmark.stories), 3)
    for story in benchmark.stories:
      self.assertIsInstance(story, InteractivePage)
    story_names = [story.name for story in benchmark.stories]
    self.assertSequenceEqual(
        story_names, ["newtab_startup", "blank_startup", "google_startup"])

  def test_combined_stories_rejected(self) -> None:
    with self.assertRaisesRegex(argparse.ArgumentError, "--combined"):
      self.parse_args("--combined")

  def test_stories_filtering(self) -> None:
    args = self.parse_args("--stories=newtab_startup")
    benchmark = BrowserStartupBenchmark.from_cli_args(args)
    story_names = [story.name for story in benchmark.stories]
    self.assertSequenceEqual(story_names, ["newtab_startup"])

  def test_stories_filtering_exclude(self) -> None:
    args = self.parse_args("--stories=.*,-google_startup")
    benchmark = BrowserStartupBenchmark.from_cli_args(args)
    story_names = [story.name for story in benchmark.stories]
    self.assertSequenceEqual(story_names, ["newtab_startup", "blank_startup"])

  def test_custom_page_config(self) -> None:
    config_file = pathlib.Path("custom_startup_pages.json")
    config_data = {
        "pages": {
            "custom_newtab": [{
                "action": "get",
                "url": "chrome://newtab/",
                "ready_state": "complete",
            }],
            "custom_blank": [{
                "action": "get",
                "url": "about:blank",
                "ready_state": "complete",
            }],
        },
    }
    self.fs.create_file(config_file, contents=json.dumps(config_data))
    args = self.parse_args(f"--page-config={config_file}",
                           "--stories=custom_newtab")
    benchmark = BrowserStartupBenchmark.from_cli_args(args)
    story_names = [story.name for story in benchmark.stories]
    self.assertSequenceEqual(story_names, ["custom_newtab"])

  def test_probe_compute_summary(self) -> None:
    csv_1 = pth.LocalPath(
        "/results/trace_processor/browser_window_first_paint.csv")
    df_1 = pd.DataFrame({
        "cb_browser": [
            "baseline", "baseline", "initial_webui", "initial_webui",
        ],
        "cb_story": [
            "newtab_startup", "newtab_startup", "newtab_startup",
            "newtab_startup",
        ],
        "cb_temperature": ["default", "default", "default", "default"],
        "cb_run": [0, 1, 0, 1],
        "browser_window_first_paint_ms": [100.0, 120.0, 90.0, 110.0],
    })
    self.fs.create_file(csv_1, contents=df_1.to_csv(index=False))

    empty_csv = pth.LocalPath("/results/trace_processor/reload_button_fcp.csv")
    self.fs.create_file(empty_csv, contents="")

    summary_df = BrowserStartupProbe.compute_summary([csv_1, empty_csv])
    self.assertEqual(len(summary_df), 2)
    self.assertSequenceEqual(
        list(summary_df["cb_browser"]), ["baseline", "initial_webui"])
    self.assertSequenceEqual(
        list(summary_df["median"]), [110.0, 100.0])
    self.assertSequenceEqual(
        list(summary_df["p90"]), [118.0, 108.0])
    self.assertSequenceEqual(
        list(summary_df["count"]), [2, 2])

  def test_probe_merge_and_log_browsers_result(self) -> None:
    csv_1 = pth.LocalPath(
        "/results/trace_processor/first_web_contents_non_empty_paint.csv")
    df_1 = pd.DataFrame({
        "cb_browser": ["baseline", "initial_webui"],
        "cb_story": ["newtab_startup", "newtab_startup"],
        "cb_temperature": ["default", "default"],
        "cb_run": [0, 0],
        "first_web_contents_non_empty_paint_ms": [200.0, 180.0],
    })
    self.fs.create_file(csv_1, contents=df_1.to_csv(index=False))

    benchmark = BrowserStartupBenchmark.from_cli_args(self.parse_args())
    probe = BrowserStartupProbe(benchmark=benchmark)
    tp_probe = mock.MagicMock()
    tp_probe.name = TraceProcessorProbe.NAME

    results = ProbeResultDict(pth.LocalPath("/results"))
    results[tp_probe] = LocalProbeResult(csv=(csv_1,))

    group = mock.MagicMock()
    group.results = results
    group.get_local_probe_result_path.return_value = pth.LocalPath(
        "/results/browser_startup.csv")

    merged_result = probe.merge_browsers(group)
    self.assertEqual(len(merged_result.csv_list), 1)
    summary_path = merged_result.csv
    self.assertEqual(summary_path.name, "startup_summary.csv")
    self.assertTrue(summary_path.is_file())

    results[probe] = merged_result
    with mock.patch("logging.critical") as mock_log:
      probe.log_browsers_result(group)
      mock_log.assert_called_once()
      logged_text = mock_log.call_args[0][1]
      self.assertIn("first_web_contents_non_empty_paint_ms", logged_text)
      self.assertIn("newtab_startup", logged_text)


class TestBrowserStartupCli(BaseCliTestCase):

  def test_cli_defaults_and_overrides(self) -> None:
    subcommand = BenchmarkSubcommand(
        MockCLI(platform=self.platform), BrowserStartupBenchmark)
    parser = subcommand.add_cli_arguments(CBArgumentParser())
    default_args = parser.parse_args([])
    self.assertEqual(default_args.splash_screen, SplashScreen.NONE)
    self.assertFalse(default_args.start_browser)
    self.assertEqual(
        parser.parse_args(["--splash-screen=detailed"]).splash_screen,
        SplashScreen.DETAILED)
    self.assertTrue(parser.parse_args(["--start-browser"]).start_browser)
    self.assertTrue(parser.parse_args(["--start-browser=true"]).start_browser)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
