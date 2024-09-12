# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
import unittest

from crossbench.browsers.settings import Settings
from crossbench.probes.profiling.system_profiling import (
    RENDERER_CMD_PATH, CallGraphMode, CleanupMode, ProfilingProbe, TargetMode,
    generate_simpleperf_command_line)
from tests import test_helper
from tests.crossbench.mock_browser import (MockChromeStable, MockFirefox,
                                           MockSafari)
from tests.crossbench.mock_helper import LinuxMockPlatform, MacOsMockPlatform
from tests.crossbench.probes.helper import GenericProbeTestCase


class SystemProfilingProbeTestCase(GenericProbeTestCase):

  def setUp(self):
    super().setUp()
    self.fs.add_real_file(RENDERER_CMD_PATH)

  def test_simpleperf_command_line_with_tid(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.RENDERER_MAIN_ONLY,
            app_name="com.android.chrome",
            renderer_pid=1234,
            renderer_main_tid=5678,
            call_graph_mode=CallGraphMode.DWARF,
            frequency=None,
            count=None,
            cpus=None,
            events=None,
            grouped_events=None,
            add_counters=None,
            output_path=output_path), [
                "simpleperf", "record", "-t", "5678", "--call-graph", "dwarf", "--post-unwind=yes", "-o",
                output_path
            ])

  def test_simpleperf_command_line_with_pid(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.RENDERER_PROCESS_ONLY,
            app_name="com.android.chrome",
            renderer_pid=1234,
            renderer_main_tid=5678,
            call_graph_mode=CallGraphMode.DWARF,
            frequency=None,
            count=None,
            cpus=None,
            events=None,
            grouped_events=None,
            add_counters=None,
            output_path=output_path), [
                "simpleperf", "record", "-p", "1234", "--call-graph", "dwarf", "--post-unwind=yes", "-o",
                output_path
            ])

  def test_simpleperf_command_line_with_app(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.BROWSER_APP_ONLY,
            app_name="com.chrome.beta",
            renderer_pid=None,
            renderer_main_tid=None,
            call_graph_mode=CallGraphMode.DWARF,
            frequency=None,
            count=None,
            cpus=None,
            events=None,
            grouped_events=None,
            add_counters=None,
            output_path=output_path), [
                "simpleperf", "record", "--app", "com.chrome.beta",
                "--call-graph", "dwarf", "--post-unwind=yes", "-o", output_path
            ])

  def test_simpleperf_command_line_systemwide(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.SYSTEM_WIDE,
            app_name="org.chromium.chrome",
            renderer_pid=None,
            renderer_main_tid=None,
            call_graph_mode=CallGraphMode.DWARF,
            frequency=None,
            count=None,
            cpus=None,
            events=None,
            grouped_events=None,
            add_counters=None,
            output_path=output_path),
        ["simpleperf", "record", "-a", "--call-graph", "dwarf", "--post-unwind=yes", "-o", output_path])

  def test_simpleperf_command_line_with_frequency(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.SYSTEM_WIDE,
            app_name="org.chromium.chrome",
            renderer_pid=None,
            renderer_main_tid=None,
            call_graph_mode=CallGraphMode.FRAME_POINTER,
            frequency=1234,
            count=None,
            cpus=None,
            events=None,
            grouped_events=None,
            add_counters=None,
            output_path=output_path), [
                "simpleperf", "record", "-a", "--call-graph", "fp", "-f",
                "1234", "-o", output_path
            ])

  def test_simpleperf_command_line_with_count(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.SYSTEM_WIDE,
            app_name="org.chromium.chrome",
            renderer_pid=None,
            renderer_main_tid=None,
            call_graph_mode=CallGraphMode.FRAME_POINTER,
            frequency=None,
            count=5,
            cpus=None,
            events=None,
            grouped_events=None,
            add_counters=None,
            output_path=output_path), [
                "simpleperf", "record", "-a", "--call-graph", "fp", "-c", "5",
                "-o", output_path
            ])

  def test_simpleperf_command_line_with_cpu(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.SYSTEM_WIDE,
            app_name="org.chromium.chrome",
            renderer_pid=None,
            renderer_main_tid=None,
            call_graph_mode=CallGraphMode.FRAME_POINTER,
            frequency=None,
            count=None,
            cpus=[0, 1, 2],
            events=None,
            grouped_events=None,
            add_counters=None,
            output_path=output_path), [
                "simpleperf", "record", "-a", "--call-graph", "fp", "--cpu",
                "0,1,2", "-o", output_path
            ])

  def test_simpleperf_command_line_with_events(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.SYSTEM_WIDE,
            app_name="org.chromium.chrome",
            renderer_pid=None,
            renderer_main_tid=None,
            call_graph_mode=CallGraphMode.NO_CALL_GRAPH,
            frequency=1234,
            count=5,
            cpus=None,
            events=["cpu-cycles", "instructions"],
            grouped_events=None,
            add_counters=None,
            output_path=output_path), [
                "simpleperf", "record", "-a", "-f", "1234", "-c", "5", "-e",
                "cpu-cycles,instructions", "-o", output_path
            ])

  def test_simpleperf_command_line_with_grouped_events(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.SYSTEM_WIDE,
            app_name="org.chromium.chrome",
            renderer_pid=None,
            renderer_main_tid=None,
            call_graph_mode=CallGraphMode.NO_CALL_GRAPH,
            frequency=1234,
            count=5,
            cpus=None,
            events=None,
            grouped_events=["cpu-cycles", "instructions"],
            add_counters=None,
            output_path=output_path), [
                "simpleperf", "record", "-a", "-f", "1234", "-c", "5",
                "--group", "cpu-cycles,instructions", "-o", output_path
            ])

  def test_simpleperf_command_line_with_add_counters(self):
    output_path = pathlib.Path("simpleperf.perf.data")
    self.assertListEqual(
        generate_simpleperf_command_line(
            target=TargetMode.SYSTEM_WIDE,
            app_name="org.chromium.chrome",
            renderer_pid=None,
            renderer_main_tid=None,
            call_graph_mode=CallGraphMode.NO_CALL_GRAPH,
            frequency=1234,
            count=5,
            cpus=None,
            events=["sched:sched_switch"],
            grouped_events=None,
            add_counters=["cpu-cycles", "instructions"],
            output_path=output_path), [
                "simpleperf", "record", "-a", "-f", "1234", "-c", "5", "-e",
                "sched:sched_switch", "--add-counter",
                "cpu-cycles,instructions", "--no-inherit", "-o", output_path
            ])

  def test_create_non_defaults(self):
    probe = ProfilingProbe.from_config({
        "js": False,
        "browser_process": True,
        "spare_renderer_process": True,
        "v8_interpreted_frames": False,
        "pprof": False,
        "cleanup": "never",
        "target": "renderer_process_only",
        "pin_renderer_main_core": 3,
        "call_graph_mode": "dwarf",
        "frequency": 1200,
        "count": 430,
        "cpu": [1, 2, 3],
        "events": ["instructions", "cache-misses"],
        "grouped_events": ["cache-references", "cache-misses"],
        "add_counters": ["aa", "bb"],
    })
    self.assertFalse(probe.sample_js)
    self.assertTrue(probe.sample_browser_process)
    self.assertFalse(probe.run_pprof)
    self.assertTrue(probe.cleanup_mode, CleanupMode.NEVER)
    self.assertEqual(probe.target, TargetMode.RENDERER_PROCESS_ONLY)
    self.assertTrue(probe.start_profiling_after_setup)
    self.assertEqual(probe.pin_renderer_main_core, 3)
    self.assertEqual(probe.call_graph_mode, CallGraphMode.DWARF)
    self.assertEqual(probe.frequency, 1200)
    self.assertEqual(probe.count, 430)
    self.assertEqual(probe.cpu, (1, 2, 3))
    self.assertEqual(probe.events, ("instructions", "cache-misses"))
    self.assertEqual(probe.grouped_events, ("cache-references", "cache-misses"))
    self.assertEqual(probe.add_counters, ("aa", "bb"))

  def test_spare_renderer(self):
    browser_a = self.browsers[0]
    browser_b = self.browsers[0]

    probe_spare = ProfilingProbe(spare_renderer_process=True)
    browser_a.attach_probe(probe_spare)
    self.assertNotIn("SpareRendererForSitePerProcess",
                     browser_b.features.disabled)

    probe_no_spare = ProfilingProbe(spare_renderer_process=False)
    browser_b.attach_probe(probe_no_spare)
    self.assertIn("SpareRendererForSitePerProcess", browser_b.features.disabled)

  def test_attach_unsupported(self):
    probe = ProfilingProbe()

    macos_platform = MacOsMockPlatform()
    TEST_BROWSERS = (MockSafari, MockFirefox, MockChromeStable)
    for browser_cls in TEST_BROWSERS:
      browser_cls.setup_fs(self.fs, macos_platform)
      name = browser_cls.__name__
      browser_cls(
          name, settings=Settings(platform=macos_platform)).attach_probe(probe)

    linux_platform = LinuxMockPlatform()
    for browser_cls in TEST_BROWSERS:
      browser_cls.setup_fs(self.fs, linux_platform)
    with self.assertRaises(AssertionError):
      MockFirefox(
          "firefox",
          settings=Settings(platform=linux_platform)).attach_probe(probe)
    MockChromeStable(
        "chrome",
        settings=Settings(platform=linux_platform)).attach_probe(probe)


class EnumTestCase(unittest.TestCase):

  def test_cleanup_mode(self):
    self.assertIs(CleanupMode(True), CleanupMode.ALWAYS)
    self.assertIs(CleanupMode(False), CleanupMode.NEVER)

    self.assertIs(CleanupMode("always"), CleanupMode.ALWAYS)
    self.assertIs(CleanupMode("never"), CleanupMode.NEVER)
    self.assertIs(CleanupMode("auto"), CleanupMode.AUTO)

  def test_target_mode(self):
    self.assertIs(
        TargetMode("renderer_main_only"), TargetMode.RENDERER_MAIN_ONLY)
    self.assertIs(
        TargetMode("RENDERER_MAIN_ONLY"), TargetMode.RENDERER_MAIN_ONLY)

  def test_call_graph_mode(self):
    self.assertIs(CallGraphMode("frame_pointer"), CallGraphMode.FRAME_POINTER)
    self.assertIs(CallGraphMode("FRAME_POINTER"), CallGraphMode.FRAME_POINTER)

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
