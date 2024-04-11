# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
import unittest

from crossbench.probes.profiling.system_profiling import generate_simpleperf_command_line, TargetMode
from tests import test_helper


class TestProbe(unittest.TestCase):

  def test_simpleperf_command_line(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.RENDERER_MAIN_ONLY,
            app_name="com.android.chrome",
            renderer_pid=1234,
            renderer_main_tid=5678,
            frame_pointers=False,
            output_path=output_path), [
                "simpleperf", "record", "-t", "5678", "--post-unwind=yes", "-o",
                output_path
            ])
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.RENDERER_PROCESS_ONLY,
            app_name="com.android.chrome",
            renderer_pid=1234,
            renderer_main_tid=5678,
            frame_pointers=False,
            output_path=output_path), [
                "simpleperf", "record", "-p", "1234", "--post-unwind=yes", "-o",
                output_path
            ])
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.BROWSER_APP_ONLY,
            app_name="com.chrome.beta",
            renderer_pid=None,
            renderer_main_tid=None,
            frame_pointers=False,
            output_path=output_path), [
                "simpleperf", "record", "--app", "com.chrome.beta",
                "--post-unwind=yes", "-o", output_path
            ])
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.SYSTEM_WIDE,
            app_name="org.chromium.chrome",
            renderer_pid=None,
            renderer_main_tid=None,
            frame_pointers=True,
            output_path=output_path),
        ["simpleperf", "record", "-a", "--call-graph", "fp", "-o", output_path])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
