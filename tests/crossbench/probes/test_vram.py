# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import threading
from unittest import mock

from crossbench.browsers.browser import Browser
from crossbench.probes.vram import VramProbe, VramProbeContext
from crossbench.runner.run import Run
from tests import test_helper
from tests.crossbench.probes.helper import BaseProbeTestCase


class VramProbeTestCase(BaseProbeTestCase):

  def test_vram_probe(self):
    mock_returns = [
        {
            "gpu_0": 100.0
        },
        {
            "gpu_0": 150.0
        },
        {
            "gpu_0": 200.0
        },
        {
            "gpu_0": 120.0
        },
    ] + [{
        "gpu_0": 120.0
    }] * 10

    self.platform.gpu_vram_used = mock.Mock(side_effect=mock_returns)

    probe = VramProbe(interval=dt.timedelta(seconds=0.1))

    mock_browser = mock.Mock(spec=Browser)
    mock_browser.platform = self.platform
    mock_browser.host_platform = self.platform

    result_dir = self.platform.path("/results")
    self.fs.create_dir(result_dir)
    result_path = result_dir / "vram.json"

    mock_run = mock.Mock(spec=Run)
    mock_run.browser = mock_browser
    mock_run.get_default_probe_result_path = mock.Mock(return_value=result_path)
    mock_run.results = mock.Mock()

    mock_actions = mock.MagicMock()
    mock_run.actions = mock.MagicMock(return_value=mock_actions)

    context = VramProbeContext(probe, mock_run)
    context.setup()
    context.start()

    # Use threading.Event to wait on real wall clock since time.sleep is mocked.
    threading.Event().wait(0.35)
    context.stop()

    data = context.to_json(mock_actions)
    self.assertEqual(data["gpu_0/baseline_mb"], 100.0)
    self.assertEqual(data["gpu_0/peak_mb"], 200.0)
    self.assertEqual(data["gpu_0/delta_mb"], 100.0)
    self.assertEqual(data["baseline_mb"], 100.0)
    self.assertEqual(data["peak_mb"], 200.0)
    self.assertEqual(data["delta_mb"], 100.0)

  def test_vram_probe_multi_gpu(self):
    mock_returns = [
        {
            "gpu_0": 100.0,
            "gpu_1": 200.0
        },
        {
            "gpu_0": 150.0,
            "gpu_1": 250.0
        },
        {
            "gpu_0": 300.0,
            "gpu_1": 220.0
        },
    ] + [{
        "gpu_0": 100.0,
        "gpu_1": 200.0
    }] * 10

    self.platform.gpu_vram_used = mock.Mock(side_effect=mock_returns)
    probe = VramProbe(interval=dt.timedelta(seconds=0.1))

    mock_browser = mock.Mock(spec=Browser)
    mock_browser.platform = self.platform
    mock_browser.host_platform = self.platform

    mock_run = mock.Mock(spec=Run)
    mock_run.browser = mock_browser

    mock_actions = mock.MagicMock()
    mock_run.actions = mock.MagicMock(return_value=mock_actions)

    context = VramProbeContext(probe, mock_run)
    context.setup()
    context.start()

    threading.Event().wait(0.35)
    context.stop()

    data = context.to_json(mock_actions)
    self.assertEqual(data["gpu_0/baseline_mb"], 100.0)
    self.assertEqual(data["gpu_0/peak_mb"], 300.0)
    self.assertEqual(data["gpu_0/delta_mb"], 200.0)
    self.assertEqual(data["gpu_1/baseline_mb"], 200.0)
    self.assertEqual(data["gpu_1/peak_mb"], 250.0)
    self.assertEqual(data["gpu_1/delta_mb"], 50.0)
    self.assertEqual(data["baseline_mb"], 300.0)
    self.assertEqual(data["peak_mb"], 550.0)
    self.assertEqual(data["delta_mb"], 250.0)

  def test_vram_probe_config_parser(self):
    parser = VramProbe.config_parser()
    probe = parser.parse({"interval": "2s"})
    self.assertEqual(probe.interval, dt.timedelta(seconds=2))

  def test_vram_probe_invalid_interval(self):
    with self.assertRaises(ValueError):
      VramProbe(interval=dt.timedelta(seconds=0.01))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
