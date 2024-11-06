# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import abc

from crossbench.browsers.browser import Browser
from crossbench.probes.cpu_frequency_map import CPUFrequencyMap
from crossbench.env import HostEnvironment
from crossbench.probes.env_modifier import EnvModifier
from crossbench.probes.probe import (ProbeConfigParser, ProbeContext, ProbeKeyT)
from crossbench.probes.results import EmptyProbeResult, ProbeResult
from crossbench.runner.run import Run


class FrequencyProbe(EnvModifier):
  """
  Probe to pin a frequency for certain parts of the system, e.g. CPUs and
  memory on platforms with SysFS (Linux and Android). As of 10/2024, only CPUs
  are supported. The probe can be configured as follows:

  // Probe config HJSON.
  frequency: {
    cpus: {
      cpu0: 1111,
      cpu1: "min", // Will use the minimum allowed frequency.
      cpu2: "max"  // Will use the maximum allowed frequency.
    }
  }

  Generally, the system only allows a certain set of frequency values (for CPUs
  the values can be found in [1]). Using an invalid value in the probe config
  will cause a runtime error, but also print the list of valid values. Numerical
  values can be specified as both integers (1111) and strings ("1111").

  Wildcards are supported in 2 ways:

  frequency: {
    cpus: "max"
  }


  frequency: {
    cpus: {
      // When * is used, there should be no other keys in the map.
      *: "max"
    }
  }

  Note that when running with different platforms (e.g.
  --browser=android:chrome-stable --browser=linux:chrome-stable), "*", "min"
  and "max" might mean different things for each platform.

  [1] https://docs.kernel.org/admin-guide/pm/cpufreq.html#:~:text=scaling_available_frequencies
  """

  NAME = "frequency"

  IS_GENERAL_PURPOSE = True
  PRODUCES_DATA = False

  def __init__(self, cpus: CPUFrequencyMap):
    super().__init__()
    self._cpu_frequency_map: CPUFrequencyMap = cpus

  @classmethod
  def config_parser(cls) -> ProbeConfigParser:
    parser = super().config_parser()
    parser.add_argument(
        "cpus",
        type=CPUFrequencyMap,
        default=CPUFrequencyMap.parse({}),
        help="CPU frequency map, see FrequencyProbe docs")
    return parser

  @property
  def key(self) -> ProbeKeyT:
    return super().key + (("cpus", self._cpu_frequency_map.key),)

  def validate_browser(self, env: HostEnvironment, browser: Browser) -> None:
    super().validate_browser(env, browser)
    # As long as a valid platform map can be derived, all is good.
    self._cpu_frequency_map.get_target_frequencies(browser.platform)

  @property
  def cpu_frequency_map(self) -> CPUFrequencyMap:
    return self._cpu_frequency_map

  def get_context(self, run: Run):
    return FrequencyProbeContext(self, run)


class FrequencyProbeContext(
    ProbeContext[FrequencyProbe], metaclass=abc.ABCMeta):

  def __init__(self, probe: FrequencyProbe, run: Run) -> None:
    super().__init__(probe, run)

  def start(self) -> None:
    # TODO(crbug.com/372862708): Set the values given by
    # self.probe.cpu_frequency_map.get_target_cpu_frequencies().
    pass

  def stop(self) -> None:
    # TODO(crbug.com/372862708): Restore frequencies to their original values.
    pass

  def teardown(self) -> ProbeResult:
    return EmptyProbeResult()
