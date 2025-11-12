# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest
from unittest import mock

from crossbench.cli.cli import CrossBenchCLI
from tests import test_helper


class PinpointSubcommandTest(unittest.TestCase):
  """Verifies that subcommands call the right functions."""

  def setUp(self):
    super().setUp()
    self.cli = CrossBenchCLI()
    self.patcher_print = mock.patch("builtins.print")
    self.mock_print = self.patcher_print.start()

  def tearDown(self):
    super().tearDown()
    self.patcher_print.stop()

  @mock.patch("crossbench.cli.subcommand.pinpoint.fetch_bots")
  def test_pinpoint_bots_prints_filtered_bots(self, mock_fetch_bots):
    mock_fetch_bots.return_value = [
        "linux-r350-perf", "win-10-perf", "win-11-perf"
    ]
    self.cli.run(["pinpoint", "bots", "--filter", "win"])
    self.mock_print.assert_called_once_with("win-10-perf\nwin-11-perf")

  @mock.patch("crossbench.cli.subcommand.pinpoint.fetch_benchmarks")
  def test_pinpoint_benchmarks_prints_filtered_benchmarks(
      self, mock_fetch_benchmarks):
    mock_fetch_benchmarks.return_value = [
        "speedometer2", "speedometer3", "jetstream2"
    ]
    self.cli.run(["pinpoint", "benchmarks", "--filter", "speedometer"])
    self.mock_print.assert_called_once_with("speedometer2\nspeedometer3")

  @mock.patch("crossbench.cli.subcommand.pinpoint.fetch_stories")
  def test_pinpoint_benchmarks_prints_filtered_stories(self,
                                                       mock_fetch_stories):
    mock_fetch_stories.return_value = ["story1", "story2", "default"]
    self.cli.run(["pinpoint", "stories", "speedometer3", "--filter", "story"])
    mock_fetch_stories.assert_called_once_with("speedometer3")
    self.mock_print.assert_called_once_with("story1\nstory2")

  @mock.patch("crossbench.cli.subcommand.pinpoint.list_builds")
  def test_pinpoint_list_builds(self, mock_list_builds):
    self.cli.run(["pinpoint", "builds", "linux-r350-perf", "--limit", "42"])
    mock_list_builds.assert_called_once_with("linux-r350-perf", 42)

  @mock.patch("crossbench.cli.subcommand.pinpoint.start_job")
  def test_pinpoint_start_job(self, mock_start_job):
    self.cli.run([
        *["pinpoint", "start"],
        *["--benchmark", "speedometer3"],
        *["--bot", "linux-r350-perf"],
        *["--story", "default"],
        *["--repeat", "10"],
        *["--bug-id", "12345"],
        *["--base-commit", "HEAD"],
        *["--exp-commit", "recent"],
        *["--base-patch-url", "http://base.patch"],
        *["--exp-patch-url", "http://exp.patch"],
        "--base-js-flags=--flag1",
        "--exp-js-flags=--flag2",
        *["--base-enable-features", "base_feat"],
        *["--exp-enable-features", "exp_feat"],
        *["--base-disable-features", "base_dis"],
        *["--exp-disable-features", "exp_dis"],
    ])
    mock_start_job.assert_called_with(
        benchmark="speedometer3",
        bot="linux-r350-perf",
        story="default",
        story_tags=None,
        repeat=10,
        bug_id="12345",
        base_commit="HEAD",
        exp_commit="recent",
        base_patch_url="http://base.patch",
        exp_patch_url="http://exp.patch",
        base_js_flags="--flag1",
        exp_js_flags="--flag2",
        base_enable_features="base_feat",
        exp_enable_features="exp_feat",
        base_disable_features="base_dis",
        exp_disable_features="exp_dis",
    )


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
