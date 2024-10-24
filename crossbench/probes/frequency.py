# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import abc
import argparse
from typing import Any, Dict, Union

from immutabledict import immutabledict

from crossbench import exception
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
  Android-only probe to pin a frequency for certain parts of the system, e.g.
  CPUs and memory. As of 10/2024, only CPUs are supported.  The probe can be
  configured as follows:

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

  def __init__(self, cpus: immutabledict[str, Union[ExtremeFrequency, int]]):
    super().__init__()
    self._cpu_frequency_map: immutabledict[str, Union[ExtremeFrequency,
                                                      int]] = cpus

  @classmethod
  def config_parser(cls) -> ProbeConfigParser:
    parser = super().config_parser()
    parser.add_argument(
        "cpus",
        type=FrequencyProbe.cpu_frequency_map_type,
        default=None,
        help="CPU frequency map, see FrequencyProbe docs")
    return parser

  @property
  def key(self) -> ProbeKeyT:
    return super().key + (("cpus", self._cpu_frequency_map),)

  def validate_browser(self, env: HostEnvironment, browser: Browser) -> None:
    super().validate_browser(env, browser)
    if not browser.platform.is_android:
      raise ProbeIncompatibleBrowser(
          self, browser, "FrequencyProbe is only supported on android")

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
      cls, value: Any) -> immutabledict[str, Union[ExtremeFrequency, int]]:
    if value is None:
      return immutabledict()

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

    # TODO(crbug.com/372862708): Compare keys and values against the CPU names
    # and frequencies exposed by the system. Maybe in validate_env().
    return immutabledict(typed_map)


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
