# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import pathlib
from typing import Dict, List, Type
from unittest import mock

import hjson

from crossbench import __version__
from crossbench.browsers.settings import Settings
from crossbench.cli.cli import CrossBenchCLI
from crossbench.cli.config.browser import BrowserConfig
from crossbench.cli.config.browser_variants import BrowserVariantsConfig
from crossbench.cli.config.driver import BrowserDriverType
from crossbench.network.local_file_server import LocalFileNetwork
from crossbench.probes import internal
from tests import test_helper
from tests.crossbench import mock_browser
from tests.crossbench.base import BaseCliTestCase, SysExitTestException


class CliSlowTestCase(BaseCliTestCase):
  """Collection of slower tests that are not worth running
  as part of the presubmit"""

  def test_subcommand_help(self):
    for benchmark_cls in CrossBenchCLI.BENCHMARKS:
      subcommands = (benchmark_cls.NAME,) + benchmark_cls.aliases()
      for subcommand in subcommands:
        with self.assertRaises(SysExitTestException) as cm:
          self.run_cli(subcommand, "--help")
        self.assertEqual(cm.exception.exit_code, 0)
        _, stdout, stderr = self.run_cli_output(
            subcommand, "--help", raises=SysExitTestException)
        self.assertFalse(stderr)
        self.assertIn("--env-validation ENV_VALIDATION", stdout)

  def test_subcommand_help_subcommand(self):
    for benchmark_cls in CrossBenchCLI.BENCHMARKS:
      subcommands = (benchmark_cls.NAME,) + benchmark_cls.aliases()
      for subcommand in subcommands:
        with self.assertRaises(SysExitTestException) as cm:
          self.run_cli(subcommand, "help")
        self.assertEqual(cm.exception.exit_code, 0)
        _, stdout, stderr = self.run_cli_output(
            subcommand, "help", raises=SysExitTestException)
        self.assertFalse(stderr)
        self.assertIn("--env-validation ENV_VALIDATION", stdout)

  def test_subcommand_describe_subcommand(self):
    for benchmark_cls in CrossBenchCLI.BENCHMARKS:
      subcommands = (benchmark_cls.NAME,) + benchmark_cls.aliases()
      for subcommand in subcommands:
        with self.assertRaises(SysExitTestException) as cm:
          self.run_cli(subcommand, "describe")
        self.assertEqual(cm.exception.exit_code, 0)
        _, stdout, stderr = self.run_cli_output(
            subcommand, "describe", raises=SysExitTestException)
        output = stderr + stdout
        self.assertIn("See `describe benchmark ", output)

  def test_browser_identifiers(self):
    browsers: Dict[str, Type[mock_browser.MockBrowser]] = {
        "chrome": mock_browser.MockChromeStable,
        "chrome-stable": mock_browser.MockChromeStable,
        "chr-stable": mock_browser.MockChromeStable,
        "chrome-beta": mock_browser.MockChromeBeta,
        "chr-beta": mock_browser.MockChromeBeta,
        "chrome-dev": mock_browser.MockChromeDev,
        "edge": mock_browser.MockEdgeStable,
        "edge-stable": mock_browser.MockEdgeStable,
        "edge-beta": mock_browser.MockEdgeBeta,
        "edge-dev": mock_browser.MockEdgeDev,
        "ff": mock_browser.MockFirefox,
        "firefox": mock_browser.MockFirefox,
        "firefox-dev": mock_browser.MockFirefoxDeveloperEdition,
        "firefox-developer-edition": mock_browser.MockFirefoxDeveloperEdition,
        "ff-dev": mock_browser.MockFirefoxDeveloperEdition,
        "firefox-nightly": mock_browser.MockFirefoxNightly,
        "ff-nightly": mock_browser.MockFirefoxNightly,
        "ff-trunk": mock_browser.MockFirefoxNightly,
    }
    if not self.platform.is_linux:
      browsers["chr-canary"] = mock_browser.MockChromeCanary
      browsers["chrome-canary"] = mock_browser.MockChromeCanary
      browsers["edge-canary"] = mock_browser.MockEdgeCanary
    if self.platform.is_macos:
      browsers.update({
          "safari": mock_browser.MockSafari,
          "sf": mock_browser.MockSafari,
          "safari-technology-preview": mock_browser.MockSafariTechnologyPreview,
          "sf-tp": mock_browser.MockSafariTechnologyPreview,
          "tp": mock_browser.MockSafariTechnologyPreview,
      })

    for identifier, browser_cls in browsers.items():
      out_dir = self.out_dir / identifier
      self.assertFalse(out_dir.exists())
      with mock.patch.object(
          BrowserVariantsConfig, "_get_browser_cls",
          return_value=browser_cls) as get_browser_cls:
        url = "http://test.com"
        self.run_cli("loading", f"--browser={identifier}", f"--urls={url}",
                     "--env-validation=skip", f"--out-dir={out_dir}")
        self.assertTrue(out_dir.exists())
        get_browser_cls.assert_called_once()
        result_files = list(
            out_dir.glob(f"**/{internal.ResultsSummaryProbe.NAME}.json"))
        result_file = result_files[1]
        with result_file.open(encoding="utf-8") as f:
          results = json.load(f)
        self.assertEqual(results["browser"]["version"], browser_cls.VERSION)
        self.assertIn("test.com", results["stories"])

  def test_config_file_with_network(self):
    local_server_path = pathlib.Path("custom/server")
    local_server_path.mkdir(parents=True)
    self.fs.create_file(local_server_path / "index.html", st_size=100)
    config_file = pathlib.Path("/config.hjson")
    config_data = {
        "probes": {},
        "env": {},
        "browsers": {},
        "network": str(local_server_path),
    }
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)

    browsers = []

    def get_browser(self, args: argparse.Namespace):
      session = Settings(
          platform=self.platform, network=args.network.create(self.platform))
      browsers = [
          mock_browser.MockChromeDev("dev", settings=session),
      ]
      return browsers

    with mock.patch.object(CrossBenchCLI, "_get_browsers", get_browser):
      url = "http://test.com"
      self.run_cli("loading", f"--config={config_file}", f"--urls={url}",
                   "--env-validation=skip")
      for browser in browsers:
        self.assertListEqual([url], browser.url_list[self.SPLASH_URLS_LEN:])
        assert isinstance(browser.network, LocalFileNetwork)
        network: LocalFileNetwork = browser.network
        self.assertFalse(network.is_live)
        self.assertEqual(network.path, local_server_path)

  def test_multiple_browser_compatible_flags(self):
    mock_browsers: List[Type[mock_browser.MockBrowser]] = [
        mock_browser.MockChromeStable,
        mock_browser.MockFirefox,
        mock_browser.MockChromeDev,
    ]

    def mock_get_browser_cls(browser_config: BrowserConfig):
      self.assertEqual(browser_config.driver.type, BrowserDriverType.WEB_DRIVER)
      for mock_browser_cls in mock_browsers:
        if mock_browser_cls.mock_app_path() == browser_config.path:
          return mock_browser_cls
      raise ValueError("Unknown browser path")

    for chrome_flag in ("--js-flags=--no-opt", "--enable-features=Foo",
                        "--disable-features=bar"):
      # Fail for chrome flags for non-chrome browser
      with self.assertRaises(argparse.ArgumentTypeError), mock.patch.object(
          BrowserVariantsConfig,
          "_get_browser_cls",
          side_effect=mock_get_browser_cls):
        self.run_cli("loading", "--urls=http://test.com",
                     "--env-validation=skip", "--throw", "--browser=firefox",
                     chrome_flag)
      # Fail for mixed browsers and chrome flags
      with self.assertRaises(argparse.ArgumentTypeError), mock.patch.object(
          BrowserVariantsConfig,
          "_get_browser_cls",
          side_effect=mock_get_browser_cls):
        self.run_cli("loading", "--urls=http://test.com",
                     "--env-validation=skip", "--throw", "--browser=chrome",
                     "--browser=firefox", chrome_flag)
      with self.assertRaises(argparse.ArgumentTypeError), mock.patch.object(
          BrowserVariantsConfig,
          "_get_browser_cls",
          side_effect=mock_get_browser_cls):
        self.run_cli("loading", "--urls=http://test.com",
                     "--env-validation=skip", "--throw", "--browser=chrome",
                     "--browser=firefox", "--", chrome_flag)
    # Flags for the same type are allowed.
    with self.patch_get_browser():
      self.run_cli("loading", "--urls=http://test.com", "--env-validation=skip",
                   "--throw", "--browser=chrome", "--browser=chrome-dev", "--",
                   "--js-flags=--no-opt")

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
