# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
from unittest import mock

import hjson

from crossbench import path as pth
from crossbench.cli.config.probe import ProbeConfig, ProbeListConfig
from crossbench.probes.power_sampler import PowerSamplerProbe
from crossbench.probes.v8.log import V8LogProbe
from crossbench.types import JsonDict
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


class TestProbeConfig(CrossbenchFakeFsTestCase):
  # pylint: disable=expression-not-assigned

  def parse_config(self, config_data) -> ProbeListConfig:
    probe_config_file = pth.LocalPath("/probe.config.hjson")
    with probe_config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)
    return ProbeListConfig.parse(probe_config_file)

  def test_invalid_empty(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      self.parse_config({}).probes
    with self.assertRaises(argparse.ArgumentTypeError):
      self.parse_config({"foo": {}}).probes

  def test_invalid_names(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      self.parse_config({"probes": {"invalid probe name": {}}}).probes

  def test_empty(self):
    config = self.parse_config({"probes": {}})
    self.assertListEqual(config.probes, [])

  def test_single_v8_log(self):
    js_flags = ["--log-maps", "--log-function-events"]
    config = self.parse_config(
        {"probes": {
            "v8.log": {
                "prof": True,
                "js_flags": js_flags,
            }
        }})
    self.assertTrue(len(config.probes), 1)
    probe = config.probes[0]
    assert isinstance(probe, V8LogProbe)
    for flag in js_flags + ["--log-all"]:
      self.assertIn(flag, probe.js_flags)

  def test_from_cli_args(self):
    file = pth.LocalPath("probe.config.hjson")
    js_flags = ["--log-maps", "--log-function-events"]
    config_data: JsonDict = {
        "probes": {
            "v8.log": {
                "prof": True,
                "js_flags": js_flags,
            }
        }
    }
    with file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)
    args = mock.Mock(probe_config=file)
    config = ProbeListConfig.from_cli_args(args)
    self.assertTrue(len(config.probes), 1)
    probe = config.probes[0]
    assert isinstance(probe, V8LogProbe)
    for flag in js_flags + ["--log-all"]:
      self.assertIn(flag, probe.js_flags)

  def test_inline_config(self):
    mock_d8_file = pth.LocalPath("out/d8")
    self.fs.create_file(mock_d8_file, st_size=8 * 1024)
    config_data = {"d8_binary": str(mock_d8_file)}
    args = mock.Mock(probe_config=None, throw=True, wraps=False)

    args.probe = [
        ProbeConfig.parse(f"v8.log{hjson.dumps(config_data)}"),
    ]
    config = ProbeListConfig.from_cli_args(args)
    self.assertTrue(len(config.probes), 1)
    probe = config.probes[0]
    self.assertTrue(isinstance(probe, V8LogProbe))

    args.probe = [
        ProbeConfig.parse(f"v8.log:{hjson.dumps(config_data)}"),
    ]
    config = ProbeListConfig.from_cli_args(args)
    self.assertTrue(len(config.probes), 1)
    probe = config.probes[0]
    self.assertTrue(isinstance(probe, V8LogProbe))

  def test_inline_config_invalid(self):
    mock_d8_file = pth.LocalPath("out/d8")
    self.fs.create_file(mock_d8_file)
    config_data = {"d8_binary": str(mock_d8_file)}
    trailing_brace = "}"
    with self.assertRaises(argparse.ArgumentTypeError):
      ProbeConfig.parse(f"v8.log{hjson.dumps(config_data)}{trailing_brace}")
    with self.assertRaises(argparse.ArgumentTypeError):
      ProbeConfig.parse(f"v8.log:{hjson.dumps(config_data)}{trailing_brace}")
    with self.assertRaises(argparse.ArgumentTypeError):
      ProbeConfig.parse("v8.log::")

  def test_inline_config_dir_instead_of_file(self):
    mock_dir = pth.LocalPath("some/dir")
    mock_dir.mkdir(parents=True)
    config_data = {"d8_binary": str(mock_dir)}
    args = mock.Mock(
        probe=[ProbeConfig.parse(f"v8.log{hjson.dumps(config_data)}")],
        probe_config=None,
        throw=True,
        wraps=False)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      ProbeListConfig.from_cli_args(args)
    self.assertIn(str(mock_dir), str(cm.exception))

  def test_inline_config_non_existent_file(self):
    config_data = {"d8_binary": "does/not/exist/d8"}
    args = mock.Mock(
        probe=[ProbeConfig.parse(f"v8.log{hjson.dumps(config_data)}")],
        probe_config=None,
        throw=True,
        wraps=False)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      ProbeListConfig.from_cli_args(args)
    expected_path = pth.LocalPath("does/not/exist/d8")
    self.assertIn(str(expected_path), str(cm.exception))

  def test_multiple_probes(self):
    powersampler_bin = pth.LocalPath("/powersampler.bin")
    powersampler_bin.touch()
    config = self.parse_config({
        "probes": {
            "v8.log": {
                "log_all": True,
            },
            "powersampler": {
                "bin_path": str(powersampler_bin)
            }
        }
    })
    self.assertTrue(len(config.probes), 2)
    log_probe = config.probes[0]
    assert isinstance(log_probe, V8LogProbe)
    powersampler_probe = config.probes[1]
    assert isinstance(powersampler_probe, PowerSamplerProbe)
    self.assertEqual(powersampler_probe.bin_path, powersampler_bin)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
