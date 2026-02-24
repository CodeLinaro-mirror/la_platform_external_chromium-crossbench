# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import argparse
import unittest

import crossbench.path as pth
from crossbench.cli.config.probe import ProbeConfig
from crossbench.cli.config.probe_list import ProbeListConfig
from crossbench.plt.arch import MachineArch
from crossbench.probes.all import PerfettoProbe
from crossbench.probes.perfetto.downloader import PerfettoToolDownloader
from crossbench.probes.perfetto.perfetto import TraceConfig
from protoc import trace_config_pb2
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.mock_helper import LinuxMockPlatform, \
    MacOsMockPlatform, WinMockPlatform


class TraceConfigTestCase(unittest.TestCase):

  def test_parse_preset(self):
    config = TraceConfig.parse("v8")
    self.assertIsInstance(config, TraceConfig)
    # v8 preset has some data sources
    self.assertTrue(len(config.trace_config.data_sources) > 0)

  def test_parse_dict_raw_proto(self):
    config = TraceConfig.parse({
        "buffers": [{
            "size_kb": 1024
        }],
        "data_sources": [{
            "config": {
                "name": "linux.process_stats"
            }
        }]
    })
    self.assertIsInstance(config, TraceConfig)
    self.assertEqual(len(config.trace_config.buffers), 1)
    self.assertEqual(config.trace_config.buffers[0].size_kb, 1024)
    self.assertEqual(len(config.trace_config.data_sources), 1)
    self.assertEqual(config.trace_config.data_sources[0].config.name,
                     "linux.process_stats")


class PerfettoProbeTestCase(unittest.TestCase):

  def test_parse_empty(self):
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "empty"):
      PerfettoProbe.parse_str("")

  def test_create_empty(self):
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "empty"):
      _ = PerfettoProbe()

  def test_merged_simple(self):
    probe = PerfettoProbe.parse_str("v8")
    merged = probe.trace_config
    self.assertIsInstance(merged, trace_config_pb2.TraceConfig)

  def test_merged_tags(self):
    probe = PerfettoProbe.parse_str("tag1,-tag2")
    merged = probe.trace_config
    track_event_configs = [
        ds.config.track_event_config
        for ds in merged.data_sources
        if ds.config.name == "track_event"
    ]
    self.assertEqual(len(track_event_configs), 1)
    te_config = track_event_configs[0]
    self.assertIn("tag1", te_config.enabled_tags)
    self.assertIn("tag2", te_config.disabled_tags)

  def test_merged_categories(self):
    probe = PerfettoProbe.parse_dict({
        "enabled_categories": ["cat1"],
        "disabled_categories": ["cat2"],
        "enabled_tags": ["cat4"]
    })
    merged = probe.trace_config
    self.assertIsInstance(merged, trace_config_pb2.TraceConfig)
    track_event_configs = [
        ds.config.track_event_config
        for ds in merged.data_sources
        if ds.config.name == "track_event"
    ]
    self.assertEqual(len(track_event_configs), 1)
    te_config = track_event_configs[0]
    self.assertIn("cat1", te_config.enabled_categories)
    self.assertIn("cat2", te_config.disabled_categories)
    self.assertIn("cat4", te_config.enabled_tags)

  def test_parse_dict_combined(self):
    probe = PerfettoProbe.parse_dict({
        "trace_config": "v8",
        "tags": ["tag1"],
        "categories": ["cat1"]
    })
    self.assertIsInstance(probe, PerfettoProbe)
    # v8 preset has some data sources
    self.assertTrue(len(probe.trace_config.data_sources) > 0)
    merged = probe.trace_config
    track_event_configs = [
        ds.config.track_event_config
        for ds in merged.data_sources
        if ds.config.name == "track_event"
    ]
    self.assertEqual(len(track_event_configs), 1)
    te_config = track_event_configs[0]
    self.assertIn("tag1", te_config.enabled_tags)
    self.assertIn("cat1", te_config.enabled_categories)

  def test_empty_dict_config(self):
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "empty"):
      PerfettoProbe.parse_dict({})

  def test_missing_config(self):
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "unknown 1"):
      PerfettoProbe.parse_dict({"preset": "unknown 1"})
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "unknown 1"):
      PerfettoProbe.parse_str("unknown 1")

  def test_parse_config(self):
    trace_config = """
        buffers: {
            size_kb: 1234
            fill_policy: DISCARD
        }
    """
    probe: PerfettoProbe = PerfettoProbe.parse_dict(
        {"trace_config": trace_config})
    self.assertEqual(probe.trace_config.buffers[0].size_kb, 1234)
    self.assertEqual(pth.AnyPath("perfetto"), probe.perfetto_bin)

  def test_parse_example_config(self):
    config_file = test_helper.config_dir() / "doc/probe/perfetto.config.hjson"
    self.assertTrue(config_file.is_file())
    probes = ProbeListConfig.parse(config_file).probes
    self.assertEqual(len(probes), 1)
    probe = probes[0]
    self.assertIsInstance(probe, PerfettoProbe)

  def test_trace_config_preset_invalid_file(self):
    trace_config_dir = test_helper.config_dir() / "probe/perfetto/trace_config"
    for config_file in trace_config_dir.glob("*.pbtxt"):
      self.fail(f"Invalid preset file extension, use .textpb: {config_file}")

  def test_trace_config_preset(self):
    trace_config_dir = test_helper.config_dir() / "probe/perfetto/trace_config"
    preset_count = 0
    for config_file in trace_config_dir.glob("*.txtpb"):
      preset_count += 1
      with self.subTest(config_file=str(config_file)):
        probe_a = PerfettoProbe.parse_dict({"trace_config": config_file.stem})
        probe_b = PerfettoProbe.parse_str(config_file.stem)
        probe_c = PerfettoProbe.parse_str(str(config_file))
        self.assertEqual(probe_a.trace_config, probe_b.trace_config)
        self.assertEqual(probe_a.trace_config, probe_c.trace_config)
        for data_source in probe_b.trace_config.data_sources:
          config = data_source.config
          self.assertNotEqual(
              config.name, "org.chromium.trace_metadata",
              "Please use the new org.chromium.trace_metadata2 data_source "
              "without the added json-serialized categories.")
          self.assertFalse(
              config.chrome_config and config.chrome_config.trace_config,
              "Please use the org.chromium.trace_metadata2 data source "
              "which does not require the json-serialized trace_config")
    self.assertGreater(preset_count, 0)

  def test_preset_file_from_probe_config(self):
    trace_config_file = TraceConfig.preset_dir() / "v8.txtpb"
    self.assertTrue(trace_config_file.is_file())
    probe = PerfettoProbe.parse_str(str(trace_config_file))
    probe_a = ProbeConfig.parse("perfetto:v8").new_instance()
    self.assertTrue(trace_config_file.is_file())
    src_str = f"perfetto:{trace_config_file}"
    probe_b = ProbeConfig.parse(src_str).new_instance()
    self.assertEqual(probe, probe_a)
    self.assertEqual(probe, probe_b)


class PerfettoToolDownloaderTestCase(CrossbenchFakeFsTestCase):

  def test_download_linux(self):
    platform = LinuxMockPlatform()
    self._download_perfetto_tool(platform, "linux-arm64")
    platform = LinuxMockPlatform()
    platform.machine = MachineArch.ARM_32
    self._download_perfetto_tool(platform, "linux-arm")
    platform = LinuxMockPlatform()
    platform.machine = MachineArch.X64
    self._download_perfetto_tool(platform, "linux-x64")

  def test_download_macos(self):
    platform = MacOsMockPlatform()
    self._download_perfetto_tool(platform, "mac-arm64")
    platform = MacOsMockPlatform()
    platform.machine = MachineArch.X64
    self._download_perfetto_tool(platform, "mac-amd64")

  def test_download_win_invalid(self):
    platform = WinMockPlatform()
    with self.assertRaises(ValueError):
      self._download_perfetto_tool(platform, "win-arm64")

  def _download_perfetto_tool(self, platform, key):
    platform.use_mock_name = False
    download_path = platform.cache_dir("perfetto") / "v53.0/traceconv"
    platform.expect_download(
        "https://commondatastorage.googleapis.com/perfetto-luci-artifacts/"
        f"v53.0/{key}/traceconv", download_path)
    platform.expect_sh(
        download_path,
        "--version",
        result=("Perfetto v53.0-7a9a6a0 "
                "(7a9a6a0587348bffd1796b66a1da33cc1ea421d8)"))
    result = PerfettoToolDownloader("traceconv", platform=platform).download()
    self.assertTrue(platform.exists(result))
    # downloading the same will use the locally cached version
    result = PerfettoToolDownloader("traceconv", platform=platform).download()
    self.assertTrue(platform.exists(result))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
