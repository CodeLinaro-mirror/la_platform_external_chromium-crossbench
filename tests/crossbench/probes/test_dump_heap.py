# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from crossbench.path import AnyPath
from crossbench.probes.dump_heap import DumpHeapProbe, DumpHeapProbeContext
from crossbench.runner.run import Run
from tests import test_helper
from tests.crossbench.probes.helper import GenericProbeTestCase


class DumpHeapProbeTestCase(GenericProbeTestCase):

  @patch("crossbench.probes.dump_heap.dt.datetime")
  def test_invoke_basic(self, mock_datetime):
    mock_datetime.now.return_value = datetime(year=1984, month=6, day=14)

    probe = DumpHeapProbe.config_parser().parse({})

    result_path = AnyPath("/results/dump_heap")
    mock_run = MagicMock(spec=Run)
    mock_run.get_default_probe_result_path.return_value = result_path

    context = DumpHeapProbeContext(probe, mock_run)
    context.invoke(
        info_stack=("test",), timeout=timedelta(seconds=1), type="java")

    hprof_path = result_path / "test_1984-06-14_000000.prof"
    mock_datetime.now.assert_called_once()
    mock_run.browser.dump_java_heap.assert_called_once_with(hprof_path)
    self.assertListEqual(context._results, [hprof_path])

  def test_invoke_all_args(self):
    probe = DumpHeapProbe.config_parser().parse({})

    result_path = AnyPath("/results/dump_heap")
    mock_run = MagicMock(spec=Run)
    mock_run.get_default_probe_result_path.return_value = result_path

    context = DumpHeapProbeContext(probe, mock_run)
    context.invoke(
        info_stack=("test",),
        timeout=timedelta(seconds=1),
        type="java",
        identifier="identifier",
        suffix="suffix")

    hprof_path = result_path / "test_suffix.prof"
    mock_run.browser.platform.dump_java_heap.assert_called_once_with(
        "identifier", hprof_path)
    self.assertListEqual(context._results, [hprof_path])

  def test_invoke_invalid_type(self):
    probe = DumpHeapProbe.config_parser().parse({})

    result_path = AnyPath("/results/dump_heap")
    mock_run = MagicMock(spec=Run)
    mock_run.get_default_probe_result_path.return_value = result_path

    context = DumpHeapProbeContext(probe, mock_run)
    with self.assertRaises(argparse.ArgumentTypeError):
      context.invoke(
          info_stack=("test",),
          timeout=timedelta(seconds=1),
          type="invalid",
          identifier="identifier",
          suffix="suffix")

  def test_invoke_invalid_arg(self):
    probe = DumpHeapProbe.config_parser().parse({})

    result_path = AnyPath("/results/dump_heap")
    mock_run = MagicMock(spec=Run)
    mock_run.get_default_probe_result_path.return_value = result_path

    context = DumpHeapProbeContext(probe, mock_run)

    with self.assertRaisesRegex(RuntimeError,
                                "Got unexpected keyword arguments"):
      context.invoke(
          info_stack=("test",),
          timeout=timedelta(seconds=1),
          type="java",
          invalid_arg=123)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
