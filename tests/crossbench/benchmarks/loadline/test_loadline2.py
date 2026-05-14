# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pandas as pd

from crossbench.benchmarks.loadline.loadline_2 import process_scores
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase


class TestLoadLine2Helpers(BaseCrossbenchTestCase):

  def test_process_scores_single_run(self) -> None:
    query_result = pd.DataFrame(
        columns=[
            "value",
            "cb_browser",
            "metric",
            "cb_story",
            "cb_temperature",
            "cb_run",
        ],
        data=[
            [4.0, "chrome", "metric1", "story1", 0, 0],
            [16.0, "chrome", "metric2", "story2", 0, 0],
        ],
    )
    scores = process_scores(query_result, expected_metrics=2)

    self.assertEqual(scores.shape, (3, 1))
    self.assertEqual(scores["chrome"].loc["metric1"], "4.000")
    self.assertEqual(scores["chrome"].loc["metric2"], "16.000")
    self.assertEqual(scores["chrome"].loc["TOTAL_SCORE"], "8.000")

  def test_process_scores_multiple_runs(self) -> None:
    query_result = pd.DataFrame(
        columns=[
            "value",
            "cb_browser",
            "metric",
            "cb_story",
            "cb_temperature",
            "cb_run",
        ],
        data=[
            [4.0, "chrome", "metric1", "story1", 0, 0],
            [6.0, "chrome", "metric1", "story1", 0, 1],
        ],
    )
    scores = process_scores(query_result)

    self.assertEqual(scores["chrome"].loc["metric1"], "5.000 ± 12.706")

  def test_process_scores_globo_coefficient(self) -> None:
    query_result = pd.DataFrame(
        columns=[
            "value",
            "cb_browser",
            "metric",
            "cb_story",
            "cb_temperature",
            "cb_run",
        ],
        data=[
            [80.0, "chrome", "globo_homepage_interactive", "story1", 0, 0],
            [120.0, "chrome", "globo_homepage_interactive", "story1", 0, 1],
        ],
    )
    scores = process_scores(query_result, expected_metrics=1)

    self.assertEqual(scores["chrome"].loc["globo_homepage_interactive"],
                     "58.000 ± 147.392")
    self.assertEqual(scores["chrome"].loc["TOTAL_SCORE"], "58.000 ± 147.392")

  def test_process_scores_not_enough_metrics(self) -> None:
    query_result = pd.DataFrame(
        columns=[
            "value",
            "cb_browser",
            "metric",
            "cb_story",
            "cb_temperature",
            "cb_run",
        ],
        data=[
            [100.0, "chrome", "metric1", "story1", 0, 0],
        ],
    )
    scores = process_scores(query_result, expected_metrics=2)

    self.assertEqual(scores["chrome"].loc["metric1"], "100.000")
    self.assertNotIn("TOTAL_SCORE", scores["chrome"])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
