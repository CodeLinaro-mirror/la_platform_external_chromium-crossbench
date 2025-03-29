# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
from typing import cast

import crossbench.path as pth
from crossbench.cli.config.probe_list import ProbeListConfig
from crossbench.probes.all import TracingProbe
from crossbench.probes.perfetto.tracing import (MINIMAL_CONFIG, RecordFormat,
                                                RecordMode)
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


class TracingProbeTestCase(CrossbenchFakeFsTestCase):

  def test_parse_empty_config(self):
    probe: TracingProbe = TracingProbe.from_config({})
    self.assertEqual(probe.categories, MINIMAL_CONFIG)
    self.assertEqual(probe.record_mode, RecordMode.CONTINUOUSLY)
    self.assertEqual(probe.record_format, RecordFormat.PROTO)
    self.assertEqual(probe.startup_duration, 0)

  def test_parse_config(self):
    probe: TracingProbe = TracingProbe.from_config(
        {"categories": ["one", "two"]})
    self.assertEqual(probe.categories, {"one", "two"} | MINIMAL_CONFIG)
    self.assertEqual(probe.record_mode, RecordMode.CONTINUOUSLY)
    self.assertEqual(probe.record_format, RecordFormat.PROTO)
    self.assertEqual(probe.startup_duration, 0)

  def test_parse_config_empty(self):
    probe: TracingProbe = TracingProbe.from_config({
        "preset": "empty",
        "categories": ["one", "two"]
    })
    self.assertEqual(probe.categories, {"one", "two"})

  def test_parse_trace_config_file_invalid(self):
    trace_config_file = pth.LocalPath("trace_config_file.json")
    with self.assertRaises(argparse.ArgumentTypeError):
      TracingProbe.from_config({"trace_config": str(trace_config_file)})

    with trace_config_file.open("w", encoding="utf-8") as f:
      json.dump({}, f)
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "trace_config"):
      TracingProbe.from_config({"trace_config": str(trace_config_file)})

    with trace_config_file.open("w", encoding="utf-8") as f:
      json.dump({"trace_config": {}}, f)
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "startup_duration"):
      TracingProbe.from_config({"trace_config": str(trace_config_file)})

    with trace_config_file.open("w", encoding="utf-8") as f:
      json.dump({"startup_duration": 0, "trace_config": {}}, f)
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "startup_duration"):
      TracingProbe.from_config({"trace_config": str(trace_config_file)})

    with trace_config_file.open("w", encoding="utf-8") as f:
      json.dump({"startup_duration": 10, "trace_config": {}}, f)
    with self.assertRaisesRegex(argparse.ArgumentTypeError,
                                "no trace categories"):
      TracingProbe.from_config({"trace_config": str(trace_config_file)})

    with trace_config_file.open("w", encoding="utf-8") as f:
      json.dump(
          {
              "startup_duration": 10,
              "trace_config": {},
              "result_file": "path/to/result"
          }, f)
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "result_file"):
      TracingProbe.from_config({"trace_config": str(trace_config_file)})

  def test_parse_trace_config_file(self):
    trace_config_file = pth.LocalPath("trace_config_file.json")
    with trace_config_file.open("w", encoding="utf-8") as f:
      json.dump(
          {
              "startup_duration": 10,
              "trace_config": {
                  "included_categories": ["one", "two"]
              }
          }, f)
    probe: TracingProbe = TracingProbe.from_config(
        {"trace_config": str(trace_config_file)})
    self.assertFalse(probe.categories)
    trace_config_file = probe.trace_config_file
    self.assertIsNotNone(trace_config_file)
    self.assertTrue(trace_config_file.is_file())
    self.assertEqual(trace_config_file, trace_config_file)

  def test_parse_trace_config_file_conflict(self):
    trace_config_file = pth.LocalPath("trace_config_file.json")
    with trace_config_file.open("w", encoding="utf-8") as f:
      json.dump(
          {
              "startup_duration": 10,
              "trace_config": {
                  "included_categories": ["one", "two"]
              }
          }, f)
    with self.assertRaisesRegex(argparse.ArgumentTypeError,
                                "trace categories or a trace_config"):
      TracingProbe.from_config({
          "preset": "v8",
          "trace_config": str(trace_config_file)
      })
    with self.assertRaisesRegex(argparse.ArgumentTypeError,
                                "trace categories or a trace_config"):
      TracingProbe.from_config({
          "categories": ["one", "two"],
          "trace_config": str(trace_config_file)
      })

  def test_parse_example_config(self):
    config_file = test_helper.config_dir() / "doc/probe/tracing.config.hjson"
    self.fs.add_real_file(config_file)
    self.assertTrue(config_file.is_file())
    trace_config_file = config_file.parent / "trace_config_file.json"
    self.fs.add_real_file(trace_config_file)
    self.assertTrue(trace_config_file.is_file())

    probes = ProbeListConfig.parse_path(config_file).probes
    self.assertEqual(len(probes), 1)
    probe = probes[0]
    self.assertIsInstance(probe, TracingProbe)
    tracing_probe = cast(TracingProbe, probe)
    self.assertIsNotNone(tracing_probe.categories)
    self.assertTrue(tracing_probe.trace_config_file.is_file())
    self.assertEqual(tracing_probe.trace_config_file, trace_config_file)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
