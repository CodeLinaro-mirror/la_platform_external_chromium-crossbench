# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import pathlib
import unittest
from unittest import mock

import hjson

from crossbench import __version__, plt
from crossbench.cli.cli import CrossBenchCLI
from crossbench.cli.config.browser import BrowserConfig
from crossbench.cli.config.browser_variants import BrowserVariantsConfig
from crossbench.env import EnvironmentConfig
from tests import test_helper
from tests.crossbench import mock_browser
from tests.crossbench.base import BaseCliTestCase, SysExitTestException


class FastCliTestCasePartA(BaseCliTestCase):
  """These tests are run as part of the presubmit and should be
  reasonably fast.
  Slow tests run on the CQ are in CliSlowTestCase.

  Keep FastCliTestCasePartA and FastCliTestCasePartB balanced for faster local
  presubmit checks.
  """

  def test_benchmark_order(self):
    sorted_benchmark_classes = sorted(
        CrossBenchCLI.BENCHMARKS, key=lambda cls: cls.NAME)
    self.assertSequenceEqual(sorted_benchmark_classes, CrossBenchCLI.BENCHMARKS)

  def test_invalid(self):
    with self.assertRaises(SysExitTestException):
      self.run_cli("unknown subcommand", "--invalid flag")

  def test_describe_invalid_empty(self):
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("describe", "")
    self.assertEqual(cm.exception.exit_code, 0)
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("describe", "", "--json")
    self.assertEqual(cm.exception.exit_code, 0)

    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("describe", "--unknown")
    self.assertEqual(cm.exception.exit_code, 0)
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("describe", "--unknown", "--json")
    self.assertEqual(cm.exception.exit_code, 0)

  def test_describe_invalid_probe(self):
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("describe", "probe", "unknown probe")
    self.assertEqual(cm.exception.exit_code, 0)
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("describe", "probe", "unknown probe", "--json")
    self.assertEqual(cm.exception.exit_code, 0)

  def test_describe_invalid_benchmark(self):
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("describe", "benchmark", "unknown benchmark")
    self.assertEqual(cm.exception.exit_code, 0)
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("describe", "benchmark", "unknown benchmark", "--json")
    self.assertEqual(cm.exception.exit_code, 0)

  def test_describe_invalid_all(self):
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("describe", "all", "unknown probe or benchmark")
    self.assertEqual(cm.exception.exit_code, 0)
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("describe", "--json", "all", "unknown probe or benchmark")
    self.assertEqual(cm.exception.exit_code, 0)

  def test_describe(self):
    # Non-json output shouldn't fail
    self.run_cli("describe")
    self.run_cli("describe", "all")
    _, stdout, stderr = self.run_cli_output("describe", "--json")
    self.assertFalse(stderr)
    data = json.loads(stdout)
    self.assertIn("benchmarks", data)
    self.assertIn("probes", data)
    self.assertIsInstance(data["benchmarks"], dict)
    self.assertIsInstance(data["probes"], dict)

  def test_describe_benchmarks(self):
    # Non-json output shouldn't fail
    self.run_cli("describe", "benchmarks")
    _, stdout, stderr = self.run_cli_output("describe", "--json", "benchmarks")
    self.assertFalse(stderr)
    data = json.loads(stdout)
    self.assertNotIn("benchmarks", data)
    self.assertNotIn("probes", data)
    self.assertIsInstance(data, dict)
    self.assertIn("loading", data)

  def test_describe_probes(self):
    # Non-json output shouldn't fail
    self.run_cli("describe", "probes")
    _, stdout, stderr = self.run_cli_output("describe", "--json", "probes")
    self.assertFalse(stderr)
    data = json.loads(stdout)
    self.assertNotIn("benchmarks", data)
    self.assertNotIn("probes", data)
    self.assertIsInstance(data, dict)
    self.assertIn("v8.log", data)

  def test_describe_all(self):
    self.run_cli("describe", "probes")
    _, stdout, stderr = self.run_cli_output("describe", "all")
    self.assertFalse(stderr)
    self.assertIn("benchmarks", stdout)
    self.assertIn("v8.log", stdout)
    self.assertIn("speedometer", stdout)

  def test_describe_all_filtered(self):
    self.run_cli("describe", "probes")
    _, stdout, stderr = self.run_cli_output("describe", "all", "v8.log")
    self.assertFalse(stderr)
    self.assertNotIn("benchmarks", stdout)
    self.assertIn("v8.log", stdout)
    self.assertNotIn("speedometer", stdout)

  def test_describe_all_json(self):
    self.run_cli("describe", "probes")
    _, stdout, stderr = self.run_cli_output("describe", "--json", "all")
    self.assertFalse(stderr)
    data = json.loads(stdout)
    self.assertIsInstance(data, dict)
    self.assertIn("benchmarks", data)
    self.assertIn("v8.log", data["probes"])

  def test_describe_all_json_filtered(self):
    self.run_cli("describe", "probes")
    _, stdout, stderr = self.run_cli_output("describe", "--json", "all",
                                            "v8.log")
    self.assertFalse(stderr)
    data = json.loads(stdout)
    self.assertIsInstance(data, dict)
    self.assertEqual(data["benchmarks"], {})
    self.assertEqual(len(data["probes"]), 1)
    self.assertIn("v8.log", data["probes"])

  def test_help(self):
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("--help")
    self.assertEqual(cm.exception.exit_code, 0)
    _, stdout, stderr = self.run_cli_output(
        "--help", raises=SysExitTestException)
    self.assertFalse(stderr)
    self.assertIn("usage:", stdout)
    self.assertIn("Subcommands:", stdout)
    # Check for top-level option:
    self.assertIn("--no-color", stdout)
    self.assertIn("Disable colored output", stdout)
    self.assertIn("Available Probes for all Benchmarks:", stdout)

  def test_help_subcommand(self):
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("help")
    self.assertEqual(cm.exception.exit_code, 0)
    _, stdout, stderr = self.run_cli_output("help", raises=SysExitTestException)
    self.assertFalse(stderr)
    self.assertIn("usage:", stdout)
    self.assertIn("Subcommands:", stdout)
    # Check for top-level option:
    self.assertIn("--no-color", stdout)
    self.assertIn("Disable colored output", stdout)
    self.assertIn("Available Probes for all Benchmarks:", stdout)

  def test_help_subcommand_probe(self):
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("help", "v8.log")
    self.assertEqual(cm.exception.exit_code, 0)
    _, stdout, stderr = self.run_cli_output(
        "help", "v8.log", raises=SysExitTestException)
    self.assertFalse(stderr)
    self.assertIn("v8.log", stdout)
    self.assertIn("V8LogProbe", stdout)

  def test_help_subcommand_benchmark(self):
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("help", "sp3.0")
    self.assertEqual(cm.exception.exit_code, 0)
    _, stdout, stderr = self.run_cli_output(
        "help", "sp3.0", raises=SysExitTestException)
    self.assertFalse(stderr)
    self.assertIn("Speedometer 3.0", stdout)
    self.assertIn("https://browserbench.org/Speedometer3.0/", stdout)

  def test_version(self):
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("--version")
    self.assertEqual(cm.exception.exit_code, 0)
    _, stdout, stderr = self.run_cli_output(
        "--version", raises=SysExitTestException)
    self.assertFalse(stderr)
    self.assertIn(__version__, stdout)

  def test_version_subcommand(self):
    with self.assertRaises(SysExitTestException) as cm:
      self.run_cli("version")
    self.assertEqual(cm.exception.exit_code, 0)
    _, stdout, stderr = self.run_cli_output(
        "version", raises=SysExitTestException)
    self.assertFalse(stderr)
    self.assertIn(__version__, stdout)

  def test_subcommand_run_subcommand(self):
    with self.patch_get_browser():
      url = "http://test.com"
      self.run_cli("loading", "run", f"--urls={url}", "--env-validation=skip",
                   "--throw")
      for browser in self.browsers:
        self.assertListEqual([url], browser.url_list[self.SPLASH_URLS_LEN:])

  def test_invalid_probe(self):
    with self.assertRaises(argparse.ArgumentError), self.patch_get_browser():
      self.run_cli("loading", "--probe=invalid_probe_name", "--throw")

  def test_basic_probe_setting(self):
    with self.patch_get_browser():
      url = "http://test.com"
      self.run_cli("loading", "--probe=v8.log", f"--urls={url}",
                   "--env-validation=skip", "--throw")
      for browser in self.browsers:
        self.assertListEqual([url], browser.url_list[self.SPLASH_URLS_LEN:])
        self.assertIn("--log-all", browser.js_flags)

  def test_invalid_empty_probe_config_file(self):
    config_file = pathlib.Path("/config.hjson")
    config_file.touch()
    with self.patch_get_browser():
      url = "http://test.com"
      with self.assertRaises(argparse.ArgumentError) as cm:
        self.run_cli("loading", f"--probe-config={config_file}",
                     f"--urls={url}", "--env-validation=skip", "--throw")
      message = str(cm.exception)
      self.assertIn("--probe-config", message)
      self.assertIn("empty", message)
      for browser in self.browsers:
        self.assertListEqual([], browser.url_list[self.SPLASH_URLS_LEN:])
        self.assertNotIn("--log", browser.js_flags)

  def test_empty_probe_config_file(self):
    config_file = pathlib.Path("/config.hjson")
    config_data = {"probes": {}}
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)

    with self.patch_get_browser():
      url = "http://test.com"
      self.run_cli("loading", f"--probe-config={config_file}", f"--urls={url}",
                   "--env-validation=skip")
      for browser in self.browsers:
        self.assertListEqual([url], browser.url_list[self.SPLASH_URLS_LEN:])
        self.assertNotIn("--log", browser.js_flags)

  def test_invalid_probe_config_file(self):
    config_file = pathlib.Path("/config.hjson")
    config_data = {"probes": {"invalid probe name": {}}}
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)
    with self.patch_get_browser():
      url = "http://test.com"
      with self.assertRaises(argparse.ArgumentTypeError):
        self.run_cli("loading", f"--probe-config={config_file}",
                     f"--urls={url}", "--env-validation=skip", "--throw")
      for browser in self.browsers:
        self.assertListEqual([], browser.url_list)
        self.assertEqual(len(browser.js_flags), 0)

  def test_probe_config_file(self):
    config_file = pathlib.Path("/config.hjson")
    js_flags = ["--log-foo", "--log-bar"]
    config_data = {"probes": {"v8.log": {"js_flags": js_flags}}}
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)

    with self.patch_get_browser():
      url = "http://test.com"
      self.run_cli("loading", f"--probe-config={config_file}", f"--urls={url}",
                   "--env-validation=skip")
      for browser in self.browsers:
        self.assertListEqual([url], browser.url_list[self.SPLASH_URLS_LEN:])
        for flag in js_flags:
          self.assertIn(flag, browser.js_flags)

  def test_probe_config_file_invalid_probe(self):
    config_file = pathlib.Path("/config.hjson")
    config_data = {"probes": {"invalid probe name": {}}}
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)
    with self.assertRaises(
        argparse.ArgumentTypeError) as cm, self.patch_get_browser():
      self.run_cli("loading", f"--probe-config={config_file}",
                   "--urls=http://test.com", "--env-validation=skip", "--throw")
    self.assertIn("invalid probe name", str(cm.exception))

  def test_empty_config_file_properties(self):
    config_file = pathlib.Path("/config.hjson")
    config_data = {"probes": {}, "env": {}, "browsers": {}, "network": {}}
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)
    with self.assertRaises(
        argparse.ArgumentTypeError) as cm, self.patch_get_browser():
      url = "http://test.com"
      self.run_cli("loading", f"--config={config_file}", f"--urls={url}",
                   "--env-validation=skip", "--throw")
    self.assertIn("no config properties", str(cm.exception))

  def test_empty_config_files(self):
    config_file = pathlib.Path("/config.hjson")
    config_data = {}
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)
    with self.assertRaises(
        argparse.ArgumentTypeError) as cm, self.patch_get_browser():
      url = "http://test.com"
      self.run_cli("loading", f"--config={config_file}", f"--urls={url}",
                   "--env-validation=skip", "--throw")
    self.assertIn("no config properties", str(cm.exception))

  def test_conflicting_config_flags(self):
    config_file = pathlib.Path("/config.hjson")
    config_data = {"probes": {}, "env": {}, "browsers": {}, "network": {}}
    for config_flag in ("--probe-config", "--env-config", "--browser-config",
                        "--network-config"):
      with config_file.open("w", encoding="utf-8") as f:
        hjson.dump(config_data, f)
      with self.assertRaises(argparse.ArgumentTypeError) as cm:
        self.run_cli("sp2", f"--config={config_file}",
                     f"{config_flag}={config_file}", "--env-validation=skip",
                     "--throw")
      message = str(cm.exception)
      self.assertIn("--config", message)
      self.assertIn(config_flag, message)

  def test_config_file_with_probe(self):
    config_file = pathlib.Path("/config.hjson")
    js_flags = ["--log-foo", "--log-bar"]
    config_data = {
        "probes": {
            "v8.log": {
                "js_flags": js_flags
            }
        },
        "env": {},
        "browsers": {},
        "network": {},
    }
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)

    with self.patch_get_browser():
      url = "http://test.com"
      self.run_cli("loading", f"--config={config_file}", f"--urls={url}",
                   "--env-validation=skip")
      for browser in self.browsers:
        self.assertListEqual([url], browser.url_list[self.SPLASH_URLS_LEN:])
        for flag in js_flags:
          self.assertIn(flag, browser.js_flags)

  def test_config_file_with_env(self):
    config_file = pathlib.Path("/config.hjson")
    config_data = {
        "probes": {},
        "env": {
            "screen_brightness_percent": 66,
            "cpu_max_usage_percent": 77,
        },
        "browsers": {},
        "network": {},
    }
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)

    with self.patch_get_browser():
      url = "http://test.com"
      cli = self.run_cli("loading", f"--config={config_file}", f"--urls={url}",
                         "--env-validation=skip")
      for browser in self.browsers:
        self.assertListEqual([url], browser.url_list[self.SPLASH_URLS_LEN:])
        self.assertFalse(browser.js_flags)
      config = cli.runner.env.config
      self.assertEqual(config.disk_min_free_space_gib, EnvironmentConfig.IGNORE)
      self.assertEqual(config.screen_brightness_percent, 66)
      self.assertEqual(config.cpu_max_usage_percent, 77)

  def test_config_file_with_browser(self):
    config_file = pathlib.Path("/config.hjson")
    config_data = {
        "probes": {},
        "env": {},
        "browsers": {
            "browser_1": {
                "path": "chrome-dev",
            },
            "browser_2": {
                "path": "chrome-stable"
            }
        },
        "network": {},
    }
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)

    def mock_get_browser_cls(browser_config: BrowserConfig):
      path_str = str(browser_config.path).lower()
      if "dev" in path_str:
        return mock_browser.MockChromeDev
      return mock_browser.MockChromeStable

    with mock.patch.object(
        BrowserVariantsConfig,
        "get_browser_cls",
        side_effect=mock_get_browser_cls):
      url = "http://test.com"
      cli = self.run_cli("loading", f"--config={config_file}", f"--urls={url}",
                         "--env-validation=skip")
      browsers = cli.runner.browsers
      self.assertEqual(len(browsers), 2)
      self.assertEqual(browsers[0].label, "browser_1")
      self.assertEqual(browsers[1].label, "browser_2")
      for browser in browsers:
        self.assertFalse(browser.js_flags)

  def test_invalid_browser_identifier(self):
    with self.assertRaises(argparse.ArgumentError) as cm:
      self.run_cli("loading", "--browser=unknown_browser_identifier",
                   "--urls=http://test.com", "--env-validation=skip", "--throw")
    self.assertIn("--browser", str(cm.exception))
    self.assertIn("unknown_browser_identifier", str(cm.exception))

  def test_unknown_browser_binary(self):
    browser_bin = pathlib.Path("/foo/custom/browser.bin")
    browser_bin.parent.mkdir(parents=True)
    browser_bin.touch()
    with self.assertRaises(argparse.ArgumentError) as cm:
      self.run_cli("loading", f"--browser={browser_bin}",
                   "--urls=http://test.com", "--env-validation=skip", "--throw")
    self.assertIn("--browser", str(cm.exception))
    self.assertIn(str(browser_bin), str(cm.exception))

  @unittest.skipUnless(plt.PLATFORM.is_win, "Can only run on windows")
  def test_unknown_browser_binary_win(self):
    browser_bin = pathlib.Path("C:\\foo\\custom\\browser.bin")
    browser_bin.parent.mkdir(parents=True)
    browser_bin.touch()
    with self.assertRaises(argparse.ArgumentError) as cm:
      self.run_cli("loading", f"--browser={browser_bin}",
                   "--urls=http://test.com", "--env-validation=skip", "--throw")
    self.assertIn("--browser", str(cm.exception))
    self.assertIn(str(browser_bin), str(cm.exception))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
