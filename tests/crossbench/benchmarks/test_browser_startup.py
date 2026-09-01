# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from crossbench.benchmarks.loading.browser_startup import \
    BrowserStartupBenchmark
from crossbench.benchmarks.loading.config.pages import PagesConfig
from crossbench.cli.parser import CBArgumentParser
from tests import test_helper
from tests.crossbench.base import BaseCliTestCase, BaseCrossbenchTestCase

if TYPE_CHECKING:
  import argparse


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

  def test_properties(self) -> None:
    self.assertEqual(BrowserStartupBenchmark.NAME, "browser-startup")
    self.assertEqual(BrowserStartupBenchmark.aliases(), ())
    self.assertTrue(
        BrowserStartupBenchmark.default_probe_config_path().is_file())
    self.assertTrue(
        BrowserStartupBenchmark.default_pages_config_path().is_file())

  def test_get_pages_config(self) -> None:
    config = BrowserStartupBenchmark.get_pages_config()
    self.assertIsInstance(config, PagesConfig)
    self.assertEqual(len(config.pages), 3)
    page_labels = [page.label for page in config.pages]
    self.assertListEqual(page_labels,
                         ["newtab_startup", "blank_startup", "google_startup"])














class TestBrowserStartupCli(BaseCliTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.setup_config_dir(
        BrowserStartupBenchmark.default_probe_config_path().parent)




if __name__ == "__main__":
  test_helper.run_pytest(__file__)
