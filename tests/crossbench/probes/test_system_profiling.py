# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
import unittest

from crossbench.probes.profiling.system_profiling import generate_simpleperf_command_line
from tests import test_helper


class TestProbe(unittest.TestCase):

  def test_simpleperf_command_line(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            app_name="com.android.chrome",
            browser_app_only=False,
            frame_pointers=False,
            output_path=output_path),
        ["simpleperf", "record", "-a", "--post-unwind=yes", "-o", output_path])
    self.assertListEqual(
        generate_simpleperf_command_line(
            app_name="com.chrome.beta",
            browser_app_only=True,
            frame_pointers=False,
            output_path=output_path), [
                "simpleperf", "record", "--app", "com.chrome.beta",
                "--post-unwind=yes", "-o", output_path
            ])
    self.assertListEqual(
        generate_simpleperf_command_line(
            app_name="org.chromium.chrome",
            browser_app_only=True,
            frame_pointers=True,
            output_path=output_path), [
                "simpleperf", "record", "--app", "org.chromium.chrome",
                "--call-graph", "fp", "-o", output_path
            ])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
