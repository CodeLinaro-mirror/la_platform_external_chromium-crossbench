# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from crossbench.benchmarks.loading.config.blocks import ActionBlock
from crossbench.benchmarks.loading.page.live import InteractivePage
from crossbench.probes.meminfo import MeminfoProbe
from tests import test_helper
from tests.crossbench.probes.helper import GenericProbeTestCase


class TestMeminfoProbe(GenericProbeTestCase):

  def test_meminfo_dumped(self):

    actions_config = [{
        "action": "get",
        "url": "https://google.com"
    }, {
        "action": "meminfo"
    }]
    action_block = ActionBlock.parse_sequence(actions_config)
    probe = MeminfoProbe.config_parser().parse({})
    stories = [InteractivePage(name="google", blocks=tuple([action_block]))]
    runner = self.create_runner(
        stories,
        js_side_effects=[
            # setup:
            None,
            # wait for ready state
            True,
        ],
        repetitions=1)
    runner.attach_probe(probe)

    # Twice for 2 browsers
    self.platform.expect_sh(
        "date", "+%Y-%m-%d %H:%M:%S", result="2025-05-20 12:45:59")
    self.platform.expect_sh(
        "date", "+%Y-%m-%d %H:%M:%S", result="2025-05-20 12:45:59")

    runner.run()
    self.assertTrue(runner.is_success)
    meminfo_result_files = list(
        runner.out_dir.glob(f"**/{probe.name}/**/*.csv"))

    self.assertEqual(len(meminfo_result_files), 2)

    dev_meminfo = meminfo_result_files[0].read_text()
    self.assertEqual(
        dev_meminfo, "timestamp,pid,name,pss_total,rss_total,swap_total\n"
        "2025-05-20 12:45:59,1,process_1,2,3,4\n"
        "2025-05-20 12:45:59,2,process_2,3,4,5\n")

    stable_meminfo = meminfo_result_files[1].read_text()
    self.assertEqual(
        stable_meminfo, "timestamp,pid,name,pss_total,rss_total,swap_total\n"
        "2025-05-20 12:45:59,1,process_1,2,3,4\n"
        "2025-05-20 12:45:59,2,process_2,3,4,5\n")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
