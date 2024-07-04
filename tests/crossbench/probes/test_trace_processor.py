# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

import hjson
import json

from crossbench import path as pth
from crossbench import plt
from crossbench.cli.config.probe import ProbeListConfig
from crossbench.probes.all import TraceProcessorProbe
from tests import test_helper
from tests.crossbench.mock_helper import BaseCrossbenchTestCase
from crossbench.probes.results import LocalProbeResult


class TraceProcessorProbeTestCase(unittest.TestCase):

  def test_missing_probes(self):
    with self.assertRaises(ValueError) as cm:
      TraceProcessorProbe.from_config({})
    self.assertIn("probes", str(cm.exception))

  @unittest.skipIf(hjson.__name__ != "hjson", "hjson not available")
  @unittest.skipIf(not plt.PLATFORM.which("trace_processor"),
                   "trace_processor not available")
  def test_parse_config(self):
    probe: TraceProcessorProbe = TraceProcessorProbe.from_config(
        {"probes": ["perfetto", "tracing"]})
    self.assertEqual(("perfetto", "tracing"), probe.probes)

  @unittest.skipIf(hjson.__name__ != "hjson", "hjson not available")
  @unittest.skipIf(not plt.PLATFORM.which("trace_processor"),
                   "trace_processor not available")
  def test_parse_example_config(self):
    config_file = (
        test_helper.config_dir() / "doc/probe/trace_processor.config.hjson")
    self.assertTrue(config_file.is_file())
    probes = ProbeListConfig.load_path(config_file).probes
    self.assertEqual(len(probes), 2)
    probe = probes[0]
    self.assertIsInstance(probe, TraceProcessorProbe)


class TraceProcessorResultTestCase(BaseCrossbenchTestCase):

  def test_merge_browsers(self):
    self.create_file("tp")
    probe: TraceProcessorProbe = TraceProcessorProbe.from_config(
        {"probes": ["perfetto"], "trace_processor_bin": "tp"})
    browsers_run_group = unittest.mock.MagicMock()
    browsers_run_group.get_local_probe_result_path = unittest.mock.MagicMock(
        return_value=pth.LocalPath("result/"))
    story_group = unittest.mock.MagicMock()
    browsers_run_group.story_groups = [story_group]
    story_group.browser = unittest.mock.MagicMock()
    story_group.browser.label = "browser"
    rep_group = unittest.mock.MagicMock()
    story_group.repetitions_groups = [rep_group]
    rep_group.story = unittest.mock.MagicMock()
    rep_group.story.name = "story"
    run1 = unittest.mock.MagicMock()
    run2 = unittest.mock.MagicMock()
    rep_group.runs = [run1, run2]
    browsers_run_group.runs = [run1, run2]
    run1.repetition = 0
    run2.repetition = 1
    result1 = unittest.mock.MagicMock()
    result2 = unittest.mock.MagicMock()
    run1.results = {probe: result1}
    run2.results = {probe: result2}

    csv1 = self.create_file("run1/query.csv", contents='foo,bar\n1,2\n')
    csv2 = self.create_file("run2/query.csv", contents='foo,bar\n3,4\n')
    json1 = self.create_file("run1/metric.json", contents='{"foo":{"bar":7}}')
    json2 = self.create_file("run2/metric.json", contents='{"foo":{"bar":9}}')
    result1.csv_list = [csv1]
    result2.csv_list = [csv2]
    result1.json_list = [json1]
    result2.json_list = [json2]

    merged_result = probe.merge_browsers(browsers_run_group)
    self.assertEqual(len(merged_result.csv_list), 1)
    self.assertEqual(len(merged_result.json_list), 1)

    EXPECTED_CSV = (
        "browser_label,cb_story_name,repetition,foo,bar\n"
        "browser,story,0,1,2\n"
        "browser,story,1,3,4\n")
    with merged_result.csv.open("r") as f:
      self.assertEqual(f.read(), EXPECTED_CSV)

    with merged_result.json.open("r") as f:
      metrics = json.load(f)
    self.assertTrue("foo/bar" in metrics)
    self.assertTrue("values" in metrics["foo/bar"])
    self.assertEqual([7, 9], metrics["foo/bar"]["values"])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
