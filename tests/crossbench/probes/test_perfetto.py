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
      PerfettoProbe.from_config({})
    self.assertIn("config", str(cm.exception))

  def test_parse_config(self):
    probe: PerfettoProbe = PerfettoProbe.from_config({"textproto": "TEXTPROTO"})
    self.assertEqual("TEXTPROTO", probe.textproto)
    self.assertEqual(pth.AnyPath("perfetto"), probe.perfetto_bin)

  def test_parse_example_config(self):
    config_file = test_helper.config_dir() / "doc/probe/perfetto.config.hjson"
    self.assertTrue(config_file.is_file())
    probes = ProbeListConfig.parse_path(config_file).probes
    self.assertEqual(len(probes), 1)
    probe = probes[0]
    self.assertIsInstance(probe, PerfettoProbe)


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
    download_path = platform.cache_dir("perfetto") / "v49.0/traceconv"
    platform.expect_download(
        "https://commondatastorage.googleapis.com/perfetto-luci-artifacts/"
        f"v49.0/{key}/traceconv", download_path)
    platform.expect_sh(
        download_path,
        "--version",
        result=("Perfetto v49.0-33a4fd078 "
                "(33a4fd07897a9a648664926ea27769278a19ff13)"))
    result = PerfettoToolDownloader("traceconv", platform=platform).download()
    self.assertTrue(platform.exists(result))
    # downloading the same will use the locally cached version
    result = PerfettoToolDownloader("traceconv", platform=platform).download()
    self.assertTrue(platform.exists(result))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
