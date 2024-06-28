# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from typing import Final

from crossbench.benchmarks.loading.page import LivePage
from crossbench.probes.js import JSProbe
from crossbench.probes.v8.rcs import V8RCSProbe
from tests import test_helper
from tests.crossbench.probes.helper import GenericProbeTestCase

EXAMPLE_RCS_DATA: Final[str] = """
                      Runtime Function/C++ Builtin        Time             Count
========================================================================================
                                  FunctionCallback     94.96ms  38.47%     65908  29.19%
                                      JS_Execution     19.37ms   7.85%       976   0.43%
          PreParseBackgroundWithVariableResolution     14.49ms   5.87%      5175   2.29%
                              ParseFunctionLiteral     10.25ms   4.15%      2209   0.98%
                                   CompileIgnition      9.30ms   3.77%      2236   0.99%
"""


class V8RCSProbeTestCase(GenericProbeTestCase):

  def test_simple_loading_case(self):
    probe = V8RCSProbe()
    stories = [
        LivePage("google", "https://google.com"),
        LivePage("amazon", "https://amazon.com")
    ]
    repetitions = 2
    runner = self.create_runner(
        stories,
        js_side_effects=[EXAMPLE_RCS_DATA],
        repetitions=repetitions,
        separate=True,
        throw=True)
    runner.attach_probe(probe)
    runner.run()
    self.assertTrue(runner.is_success)

    for run in runner.runs:
      self.assertIn("--runtime-call-stats", run.browser.js_flags)

    js_result_files = list(runner.out_dir.glob(f"**/{probe.name}.txt"))
    # One file per story repetition
    result_count = len(self.browsers) * len(stories) * repetitions
    # One merged result per story
    result_count += len(self.browsers) * len(stories)
    # One merged results per browser
    result_count += len(self.browsers)
    self.assertEqual(len(js_result_files), result_count)

    (story_data, repetitions_data, stories_data, _) = self.get_non_empty_results_str(
        runner, probe, "txt", has_browsers_data=False)

    self.assertEqual(story_data.count(EXAMPLE_RCS_DATA), 1)
    self.assertEqual(repetitions_data.count(EXAMPLE_RCS_DATA), repetitions)
    self.assertEqual(
        stories_data.count(EXAMPLE_RCS_DATA),
        len(stories) * repetitions)

    self.assertEqual(story_data.count("== Page: "), 0)
    self.assertEqual(repetitions_data.count("== Page: "), 1)
    self.assertEqual(stories_data.count("== Page: "), len(stories))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
