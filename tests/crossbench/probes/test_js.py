# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

import hjson

from crossbench.benchmarks.loading.page import LivePage
from crossbench.cli.config.probe import ProbeListConfig
from crossbench.probes.js import JSProbe
from tests import test_helper
from tests.crossbench.probes.helper import GenericProbeTestCase


class TestJSProbe(GenericProbeTestCase):

  def test_parse_example_config(self):
    config_file = (test_helper.config_dir() / "doc/probe/js.config.hjson")
    self.fs.add_real_file(config_file)
    self.assertTrue(config_file.is_file())
    probes = ProbeListConfig.parse_path(config_file).probes
    self.assertEqual(len(probes), 1)
    probe = probes[0]
    self.assertIsInstance(probe, JSProbe)
    isinstance(probe, JSProbe)
    self.assertTrue(probe.metric_js)

  def test_parse_config(self):
    config = {
        "setup": "globalThis.metrics = {};",
        "js": "return globalThis.metrics;",
    }
    probe = JSProbe.config_parser().parse(config)
    self.assertIsInstance(probe, JSProbe)
    self.assertEqual(probe.setup_js, "globalThis.metrics = {};")
    self.assertEqual(probe.metric_js, "return globalThis.metrics;")


  def test_simple_loading_case(self):
    config = {
        "setup": "globalThis.metrics = {};",
        "js": "return globalThis.metrics;",
    }
    probe = JSProbe.config_parser().parse(config)
    stories = [
        LivePage("google", "https://google.com"),
        LivePage("amazon", "https://amazon.com")
    ]
    repetitions = 2
    runner = self.create_runner(
        stories,
        js_side_effects=[
            # setup:
            None,
            # js:
            {
                "metric1": 1.1,
                "metric2": 2.2
            }
        ],
        repetitions=repetitions,
        separate=True,
        throw=True)
    runner.attach_probe(probe)
    runner.run()
    self.assertTrue(runner.is_success)
    js_result_files = list(runner.out_dir.glob(f"**/{probe.name}.json"))
    # One file per story repetition
    result_count = len(self.browsers) * len(stories) * repetitions
    # One merged result per story
    result_count += len(self.browsers) * len(stories)
    # One merged results per browser
    result_count += len(self.browsers)
    # One top-level
    result_count += 1
    self.assertEqual(len(js_result_files), result_count)

    (story_data, repetitions_data, stories_data,
     browsers_data) = self.get_non_empty_json_results(runner, probe)
    self.assertIsInstance(story_data, dict)
    self.assertIsInstance(repetitions_data, dict)
    self.assertIsInstance(stories_data, dict)
    self.assertIsInstance(browsers_data, dict)
    # TODO: check probe result contents


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
