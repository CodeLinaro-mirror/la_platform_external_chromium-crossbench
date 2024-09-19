# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import unittest

import hjson

from crossbench import path as pth
from crossbench import plt
from crossbench.cli.config.probe import ProbeListConfig
from crossbench.probes.all import TraceProcessorProbe
from crossbench.probes.results import LocalProbeResult
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase


class TraceProcessorProbeTestCase(unittest.TestCase):

  @unittest.skipIf(not plt.PLATFORM.which("trace_processor"),
                   "trace_processor not available")
  def test_parse_example_config(self):
    config_file = (
        test_helper.config_dir() / "doc/probe/trace_processor.config.hjson")
    self.assertTrue(config_file.is_file())
    probes = ProbeListConfig.parse_path(config_file).probes
    self.assertEqual(len(probes), 2)
    probe = probes[0]
    self.assertIsInstance(probe, TraceProcessorProbe)


class TraceProcessorResultTestCase(BaseCrossbenchTestCase):

  def test_merge_browsers(self):
    probe: TraceProcessorProbe = TraceProcessorProbe.from_config("")

    browser = unittest.mock.MagicMock()
    browser.label = "browser"
    browser.unique_name = "browser"

    story = unittest.mock.MagicMock()
    story.name = "story"

    result1 = unittest.mock.MagicMock()
    csv1 = self.create_file("run1/query.csv", contents='foo,bar\n1,2\n')
    json1 = self.create_file("run1/metric.json", contents='{"foo":{"bar":7}}')
    result1.csv_list = [csv1]
    result1.json_list = [json1]

    run1 = unittest.mock.MagicMock()
    run1.repetition = 0
    run1.results = {probe: result1}
    run1.browser = browser
    run1.story = story
    run1.temperature = "default"

    result2 = unittest.mock.MagicMock()
    csv2 = self.create_file("run2/query.csv", contents='foo,bar\n3,4\n')
    json2 = self.create_file("run2/metric.json", contents='{"foo":{"bar":9}}')
    result2.csv_list = [csv2]
    result2.json_list = [json2]

    run2 = unittest.mock.MagicMock()
    run2.repetition = 1
    run2.results = {probe: result2}
    run2.browser = browser
    run2.story = story
    run2.temperature = "default"

    rep_group = unittest.mock.MagicMock()
    rep_group.story = story
    rep_group.runs = [run1, run2]

    story_group = unittest.mock.MagicMock()
    story_group.browser = browser
    story_group.repetitions_groups = [rep_group]

    browsers_run_group = unittest.mock.MagicMock()
    browsers_run_group.get_local_probe_result_path = unittest.mock.MagicMock(
        return_value=pth.LocalPath("result/"))
    browsers_run_group.story_groups = [story_group]
    browsers_run_group.runs = [run1, run2]

    merged_result = probe.merge_browsers(browsers_run_group)
    self.assertEqual(len(merged_result.csv_list), 1)
    self.assertEqual(len(merged_result.json_list), 1)

    EXPECTED_CSV = ("foo,bar,cb_browser,cb_story,cb_temperature,cb_run\n"
                    "1,2,browser,story,default,0\n"
                    "3,4,browser,story,default,1\n")
    with merged_result.csv.open("r") as f:
      self.assertEqual(f.read(), EXPECTED_CSV)

    with merged_result.json.open("r") as f:
      metrics = json.load(f)
    self.assertTrue("foo/bar" in metrics)
    self.assertTrue("values" in metrics["foo/bar"])
    self.assertEqual([7, 9], metrics["foo/bar"]["values"])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
