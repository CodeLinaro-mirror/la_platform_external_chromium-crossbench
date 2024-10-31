# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import abc
import argparse
import re
from typing import Any, Dict, Optional, Pattern, Set, Union

from immutabledict import immutabledict

from crossbench import exception
from crossbench import path as pth
from crossbench.browsers.browser import Browser
from crossbench.compat import StrEnum
from crossbench.env import HostEnvironment
from crossbench.parse import NumberParser, ObjectParser
from crossbench.probes.env_modifier import EnvModifier
from crossbench.probes.probe import (ProbeConfigParser, ProbeContext,
                                     ProbeIncompatibleBrowser, ProbeKeyT)
from crossbench.probes.results import EmptyProbeResult, ProbeResult
from crossbench.runner.run import Run


class ExtremeFrequency(StrEnum):
  MAX = "max"
  MIN = "min"


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

  Wildcards are supported:

  frequency: {
    cpus: {
      // Every CPU will be maxed out. When a wildcard is used, there should be
      // no other keys in the map.
      *: "max"
    }
  }

  [1] https://docs.kernel.org/admin-guide/pm/cpufreq.html#:~:text=scaling_available_frequencies
  """

  NAME = "frequency"

  IS_GENERAL_PURPOSE = True
  PRODUCES_DATA = False

  # Used to specify behavior for all instances of a single type at once, say
  # all CPUs.
  _WILDCARD_CONFIG_KEY = "*"

  # Directory exposing info & controls for the frequency of all CPUs.
  _CPUS_DIR: pth.AnyPosixPath = pth.AnyPosixPath("/sys/devices/system/cpu")

  # Matches the CPU names exposed by the system in _CPUS_DIR.
  _CPU_NAME_REGEX: Pattern[str] = re.compile("cpu[0-9]+$")

  def __init__(self, cpus: Dict[str, Union[ExtremeFrequency, int]]):
    super().__init__()
    self._cpu_frequency_map: immutabledict[str,
                                           Union[ExtremeFrequency,
                                                 int]] = immutabledict(cpus)

  @classmethod
  def config_parser(cls) -> ProbeConfigParser:
    parser = super().config_parser()
    parser.add_argument(
        "cpus",
        type=FrequencyProbe.cpu_frequency_map_type,
        default={},
        help="CPU frequency map, see FrequencyProbe docs")
    return parser

  @property
  def key(self) -> ProbeKeyT:
    return super().key + (("cpus", self._cpu_frequency_map),)

  def validate_browser(self, env: HostEnvironment, browser: Browser) -> None:
    super().validate_browser(env, browser)
    if not browser.platform.is_android and not browser.platform.is_linux:
      raise ProbeIncompatibleBrowser(
          self, browser, "FrequencyProbe is only supported on linux/android")

    # Check the user-selected cpus/frequencies against the ones available on
    # the device. Arguably this belongs better in validate_env(), but that
    # method only has access to the host platform, not the device.
    if not browser.platform.exists(FrequencyProbe._CPUS_DIR):
      # TODO(crbug.com/372862708): If different devices indeed use different
      # dirs, consider making this configurable in the jSON.
      raise FileNotFoundError(
          f"{FrequencyProbe._CPUS_DIR} not found. Maybe this device exposes "
          "CPUs in a different path and needs extra support.")

    available_cpu_names: Set[str] = {
        p.name
        for p in browser.platform.iterdir(FrequencyProbe._CPUS_DIR)
        if FrequencyProbe._CPU_NAME_REGEX.match(p.name)
    }
    unknown_map_names: Set[str] = (
        self._cpu_frequency_map.keys() - available_cpu_names -
        {FrequencyProbe._WILDCARD_CONFIG_KEY})
    if unknown_map_names:
      raise ValueError(f"Invalid CPU name(s): {' '.join(unknown_map_names)}. "
                       f"Available CPU(s): {' '.join(available_cpu_names)}.")

    for cpu_name in available_cpu_names:
      target_frequency: Optional[Union[
          ExtremeFrequency, int]] = self._get_target_frequency(cpu_name)
      if target_frequency is None:
        # The user selected no frequency for this CPU, proceed.
        continue

      if target_frequency in (ExtremeFrequency.MAX, ExtremeFrequency.MIN):
        # Extremes are always valid, proceed.
        continue

      single_cpu_dir: pth.AnyPosixPath = (
          FrequencyProbe._CPUS_DIR / cpu_name / "cpufreq")
      available_frequencies_file_content = browser.platform.cat(
          single_cpu_dir / "scaling_available_frequencies")
      if str(target_frequency) not in available_frequencies_file_content.rstrip(
          "\n").rstrip(" ").split(" "):
        raise ValueError(f"Target frequency {target_frequency} for {cpu_name} "
                         "is not allowed. Available frequencies: "
                         f"{available_frequencies_file_content}")

  def get_context(self, run: Run):
    return FrequencyProbeContext(self, run)

  @property
  def cpu_frequency_map(
      self) -> immutabledict[str, Union[ExtremeFrequency, int]]:
    return self._cpu_frequency_map

  # This is NOT PUBLIC, do not use outside this class! The name is chosen this
  # way because it's exposed by `./cb.py describe probe frequency`.
  @classmethod
  def cpu_frequency_map_type(
      cls, value: Any) -> Dict[str, Union[ExtremeFrequency, int]]:
    untyped_map = ObjectParser.dict(value)
    if (FrequencyProbe._WILDCARD_CONFIG_KEY in untyped_map and
        len(untyped_map) > 1):
      raise argparse.ArgumentTypeError(
          f"A wildcard ({FrequencyProbe._WILDCARD_CONFIG_KEY}) in "
          "the CPU frequency map should be the only key.")

    typed_map: Dict[str, Union[ExtremeFrequency, int]] = {}
    for k, v in untyped_map.items():
      with exception.annotate_argparsing(f"Parsing cpu frequency: {k}, {v}"):
        k = ObjectParser.non_empty_str(k)
        if v == ExtremeFrequency.MIN:
          typed_map[k] = ExtremeFrequency.MIN
          continue

        if v == ExtremeFrequency.MAX:
          typed_map[k] = ExtremeFrequency.MAX
          continue

        try:
          typed_map[k] = NumberParser.positive_zero_int(v)
        except argparse.ArgumentTypeError as e:
          raise argparse.ArgumentTypeError(
              f"Invalid value in CPU frequency map: {v}. Should "
              "have been one of \"max\"|\"min\"|<int>|\"<int>\"") from e

    return typed_map

  # Returns None if the cpu_name was not configured.
  def _get_target_frequency(
      self, cpu_name: str) -> Optional[Union[ExtremeFrequency, int]]:
    if FrequencyProbe._WILDCARD_CONFIG_KEY in self._cpu_frequency_map:
      return self._cpu_frequency_map[FrequencyProbe._WILDCARD_CONFIG_KEY]

    return self._cpu_frequency_map.get(cpu_name)



class FrequencyProbeContext(
    ProbeContext[FrequencyProbe], metaclass=abc.ABCMeta):

  def __init__(self, probe: FrequencyProbe, run: Run) -> None:
    super().__init__(probe, run)

  def start(self) -> None:
    # TODO(crbug.com/372862708): Read self.probe.cpu_frequency_map and set those
    # frequencies.
    pass

  def stop(self) -> None:
    # TODO(crbug.com/372862708): Restore frequencies to their original values.
    pass

  def teardown(self) -> ProbeResult:
    return EmptyProbeResult()
