# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
import unittest
from typing import Dict, List, Type

import hjson
from pyfakefs import fake_filesystem_unittest

import crossbench.path
from crossbench import plt
from crossbench.benchmarks.loading.loadline_presets import \
    LoadLineTabletBenchmark
from crossbench.cli.config.probe import ProbeListConfig
from crossbench.helper import ChangeCWD
from crossbench.helper.path_finder import default_chromium_candidates
from crossbench.probes.all import GENERAL_PURPOSE_PROBES
from crossbench.probes.probe import Probe
from tests import test_helper

PROBE_LOOKUP: Dict[str, Type[Probe]] = {
    probe_cls.NAME: probe_cls for probe_cls in GENERAL_PURPOSE_PROBES
}


class ProbeConfigTestCase(fake_filesystem_unittest.TestCase):
  """Parse all example probe configs in config/probe and config/doc/probe

  More detailed tests should go into dedicated probe/test_{PROBE_NAME}.py
  files.
  """

  def setUp(self) -> None:
    self.real_config_dir = test_helper.config_dir()
    super().setUp()
    self.setUpPyfakefs(modules_to_reload=[crossbench.path])
    if test_helper.is_google_env():
      self.fs.add_real_directory("/build/cas")
    self.set_up_required_paths()

  def set_up_required_paths(self):
    chrome_dir = default_chromium_candidates(plt.PLATFORM)[0]
    self.fs.create_dir(chrome_dir / "v8")
    self.fs.create_dir(chrome_dir / "chrome")
    self.fs.create_dir(chrome_dir / ".git")

    perfetto_tools = chrome_dir / "third_party/perfetto/tools"
    self.fs.create_file(perfetto_tools / "traceconv")
    self.fs.create_file(perfetto_tools / "trace_processor")

  def _test_parse_config_dir(self,
                             real_config_dir: pathlib.Path) -> List[Probe]:
    probes = []
    self.fs.add_real_directory(
        real_config_dir, lazy_read=(not test_helper.is_google_env()))
    for probe_config in real_config_dir.glob("**/*.config.hjson"):
      with ChangeCWD(probe_config.parent):
        probes += self._parse_config(probe_config)
    return probes

  def _parse_config(self, config_file: pathlib.Path) -> List[Probe]:
    probe_name = config_file.parent.name
    if probe_name not in PROBE_LOOKUP:
      probe_name = config_file.name.split(".")[0]
    probe_cls = PROBE_LOOKUP[probe_name]

    probes = ProbeListConfig.parse_path(config_file).probes
    self.assertTrue(probes)
    self.assertTrue(
        any(map(lambda probe: isinstance(probe, probe_cls), probes)))
    for probe in probes:
      self.assertFalse(probe.is_attached)
    return probes

  def test_parse_example_configs(self):
    probe_config_presets = self.real_config_dir / "probe"
    probes = self._test_parse_config_dir(probe_config_presets)
    self.assertTrue(probes)

  def test_parse_doc_configs(self):
    probe_config_doc = self.real_config_dir / "doc/probe"
    probes = self._test_parse_config_dir(probe_config_doc)
    self.assertTrue(probes)

  def test_parse_loadline_configs(self):
    probe_config = LoadLineTabletBenchmark.default_probe_config_path()
    self.fs.add_real_file(probe_config)
    probes = ProbeListConfig.parse_path(probe_config).probes
    self.assertTrue(probes)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
