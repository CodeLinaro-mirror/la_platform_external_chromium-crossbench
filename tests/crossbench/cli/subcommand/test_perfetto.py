# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import contextlib
import io
import json
import unittest
from typing import Iterator

from crossbench.cli.cli import CrossBenchCLI
from crossbench.probes.perfetto_info import CategoryDescription
from tests import test_helper


class PerfettoSubcommandTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.cli = CrossBenchCLI()
    self.subcommand = self.cli.subcommands["perfetto"]
    self.test_categories = (CategoryDescription(
        data_source="track_event",
        name="blink",
        description="Blink engine",
        tags=("benchmark", "loading")),
                            CategoryDescription(
                                data_source="track_event",
                                name="v8",
                                description="V8 engine",
                                tags=("javascript",)),
                            CategoryDescription(
                                data_source="linux.ftrace",
                                name="",
                                description="",
                                tags=()))

  @contextlib.contextmanager
  def captured_stdout(self) -> Iterator[io.StringIO]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
      yield stdout

  def test_categories_subcommand_json(self):
    args = argparse.Namespace(format="json")
    categories_subcommand = self.subcommand._categories_subcommand

    with self.captured_stdout() as fake_out:
      categories_subcommand.subcommand_run(args, self.test_categories,
                                           "mock_browser")
      output = fake_out.getvalue()

      # Verify output is valid JSON containing our categories
      parsed = json.loads(output)
      self.assertEqual(len(parsed), 2)
      self.assertEqual(parsed[0]["name"], "blink")
      self.assertEqual(parsed[1]["name"], "v8")

  def test_categories_subcommand_table(self):
    args = argparse.Namespace(format="table")
    categories_subcommand = self.subcommand._categories_subcommand

    with self.captured_stdout() as fake_out:
      categories_subcommand.subcommand_run(args, self.test_categories,
                                           "mock_browser")
      output = fake_out.getvalue()

      self.assertIn("Categories for mock_browser", output)
      self.assertIn("blink", output)
      self.assertIn("v8", output)

  def test_data_sources_subcommand_json(self):
    args = argparse.Namespace(format="json")
    data_sources_subcommand = self.subcommand._data_sources_subcommand

    with self.captured_stdout() as fake_out:
      data_sources_subcommand.subcommand_run(args, self.test_categories,
                                             "mock_browser")
      output = fake_out.getvalue()

      parsed = json.loads(output)
      self.assertIn("track_event", parsed)
      self.assertEqual(len(parsed["track_event"]), 2)

  def test_data_sources_subcommand_table(self):
    args = argparse.Namespace(format="table")
    data_sources_subcommand = self.subcommand._data_sources_subcommand

    with self.captured_stdout() as fake_out:
      data_sources_subcommand.subcommand_run(args, self.test_categories,
                                             "mock_browser")
      output = fake_out.getvalue()

      self.assertIn("Data Sources for mock_browser", output)
      self.assertIn("track_event", output)
      self.assertIn("linux.ftrace", output)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
