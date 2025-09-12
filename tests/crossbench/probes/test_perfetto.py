# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

import crossbench.path as pth
from crossbench.cli.config.probe_list import ProbeListConfig
from crossbench.plt.arch import MachineArch
from crossbench.probes.all import PerfettoProbe
from crossbench.probes.perfetto.downloader import PerfettoToolDownloader
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.mock_helper import (LinuxMockPlatform, MacOsMockPlatform,
                                          WinMockPlatform)


class PerfettoProbeTestCase(unittest.TestCase):

  def test_missing_config(self):
    with self.assertRaises(ValueError) as cm:
      PerfettoProbe.parse_dict({})
    self.assertIn("config", str(cm.exception))

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

  def test_trace_config_preset(self):
    trace_config_dir = test_helper.config_dir() / "probe/perfetto/trace_config"
    preset_count = 0
    for config_file in trace_config_dir.glob("*.pbtx"):
      preset_count += 1
      with self.subTest(config_file=str(config_file)):
        probe_a = PerfettoProbe.parse_dict({"trace_config": config_file.stem})
        probe_b = PerfettoProbe.parse_str(config_file.stem)
        self.assertEqual(probe_a.trace_config, probe_b.trace_config)
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
    with self.assertRaises(Exception):
      self._download_perfetto_tool(platform, "win-arm64")

  def _download_perfetto_tool(self, platform, key):
    platform.use_mock_name = False
    download_path = platform.cache_dir("perfetto") / "v51.2/traceconv"
    platform.expect_download(
        "https://commondatastorage.googleapis.com/perfetto-luci-artifacts/"
        f"v51.2/{key}/traceconv", download_path)
    platform.expect_sh(
        download_path,
        "--version",
        result=("Perfetto v51.2-7a9a6a0 "
                "(7a9a6a0587348bffd1796b66a1da33cc1ea421d8)"))
    result = PerfettoToolDownloader("traceconv", platform=platform).download()
    self.assertTrue(platform.exists(result))
    # downloading the same will use the locally cached version
    result = PerfettoToolDownloader("traceconv", platform=platform).download()
    self.assertTrue(platform.exists(result))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
