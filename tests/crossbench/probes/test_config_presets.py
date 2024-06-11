# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
import unittest
from typing import Dict, List, Type

import hjson
from pyfakefs import fake_filesystem_unittest

from crossbench import plt
from crossbench.helper.path_finder import default_chromium_candidates
import crossbench.path
from crossbench.cli.config.probe import ProbeListConfig
from crossbench.helper import ChangeCWD
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
    for probe_config in real_config_dir.glob("**/*.config.hjson"):
      with self.subTest(probe_config=probe_config):
        for other_files in probe_config.parent.glob(f"{probe_config.stem}*"):
          self.fs.add_real_file(other_files)
        with ChangeCWD(probe_config.parent):
          probes += self._parse_config(probe_config)
    return probes

  def _parse_config(self, config_file: pathlib.Path) -> List[Probe]:
    probe_name = config_file.parent.name
    if probe_name not in PROBE_LOOKUP:
      probe_name = config_file.name.split(".")[0]
    probe_cls = PROBE_LOOKUP[probe_name]

    probes = ProbeListConfig.load_path(config_file).probes
    self.assertTrue(probes)
    self.assertTrue(
        any(map(lambda probe: isinstance(probe, probe_cls), probes)))
    for probe in probes:
      self.assertFalse(probe.is_attached)
    return probes

  @unittest.skipIf(hjson.__name__ != "hjson", "hjson not available")
  def test_parse_example_configs(self):
    probe_config_presets = self.real_config_dir / "probe"
    probes = self._test_parse_config_dir(probe_config_presets)
    self.assertTrue(probes)

  @unittest.skipIf(hjson.__name__ != "hjson", "hjson not available")
  def test_parse_doc_configs(self):
    probe_config_doc = self.real_config_dir / "doc/probe"
    probes = self._test_parse_config_dir(probe_config_doc)
    self.assertTrue(probes)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
