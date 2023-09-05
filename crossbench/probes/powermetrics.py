# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import csv
import logging
import pathlib
import subprocess
from typing import TYPE_CHECKING, Optional, Sequence, Tuple

from crossbench import helper
from crossbench.probes.probe import (Probe, ProbeConfigParser, ProbeScope,
                                     ResultLocation)
from crossbench.probes.results import ProbeResult

if TYPE_CHECKING:
  from crossbench.browsers.browser import Browser
  from crossbench.env import HostEnvironment
  from crossbench.runner.run import Run


class SamplerType(helper.StrEnumWithHelp):
  BATTERY = ("battery", "Battery level")
  CPU_POWER = ("cpu_power",
               "CPU power and per-core frequency and idle residency")
  DISK = ("disk", "Number of read/write ops/bytes")
  GPU_POWER = ("gpu_power",
               "GPU power consumption, frequency and active residency")
  INTERRUPTS = ("interrupts", "Per-core interrupt count")
  NETWORK = ("network", "Number of in/out packets/bytes")
  TASKS = ("tasks", "Per-task stats including CPU usage and wakeups")
  THERMAL = ("thermal", "Thermal pressure state")


class PowerMetricsProbe(Probe):
  """
  Probe to collect data using macOS's powermetrics command-line tool.
  """

  NAME = "powermetrics"
  RESULT_LOCATION = ResultLocation.BROWSER
  SAMPLERS: Tuple[SamplerType,
                  ...] = (SamplerType.BATTERY, SamplerType.CPU_POWER,
                          SamplerType.DISK, SamplerType.GPU_POWER,
                          SamplerType.INTERRUPTS, SamplerType.NETWORK,
                          SamplerType.TASKS, SamplerType.THERMAL)

  @classmethod
  def config_parser(cls) -> ProbeConfigParser:
    parser = super().config_parser()
    parser.add_argument("sampling_interval", type=int, default=1000)
    parser.add_argument(
        "samplers", type=SamplerType, default=cls.SAMPLERS, is_list=True)
    return parser

  def __init__(self,
               sampling_interval: int = 0,
               samplers: Sequence[SamplerType] = SAMPLERS):
    super().__init__()
    self._sampling_interval = sampling_interval
    assert sampling_interval >= 0, (
        f"Invalid sampling_interval={sampling_interval}")
    self._samplers = tuple(samplers)

  @property
  def sampling_interval(self) -> int:
    return self._sampling_interval

  @property
  def samplers(self) -> Tuple[SamplerType, ...]:
    return self._samplers

  def is_compatible(self, browser: Browser) -> bool:
    # Only supported on macOS
    return browser.platform.is_macos

  def get_scope(self, run: Run) -> PowerMetricsProbeScope:
    return PowerMetricsProbeScope(self, run)


class PowerMetricsProbeScope(ProbeScope[PowerMetricsProbe]):

  def __init__(self, probe: PowerMetricsProbe, run: Run) -> None:
    super().__init__(probe, run)
    self._power_metrics_process: Optional[subprocess.Popen] = None
    self._output_plist_file = self.result_path.with_suffix(".plist")

  def start(self, run: Run) -> None:
    self._power_metrics_process = self.browser_platform.popen(
        "sudo",
        "powermetrics",
        "-f",
        "plist",
        f"--samplers={','.join(map(str, self.probe.samplers))}",
        "-i",
        f"{self.probe.sampling_interval}",
        "--output-file",
        self._output_plist_file,
        stdout=subprocess.DEVNULL)
    assert self._power_metrics_process is not None, (
        "Could not start powermetrics")

  def stop(self, run: Run) -> None:
    if self._power_metrics_process:
      self._power_metrics_process.terminate()

  def tear_down(self, run: Run) -> ProbeResult:
    if self._power_metrics_process:
      self._power_metrics_process.wait()
      self._power_metrics_process.kill()
    return self.browser_result(file=(self._output_plist_file,))
