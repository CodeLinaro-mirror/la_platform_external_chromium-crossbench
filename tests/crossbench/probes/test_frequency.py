# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from typing import List
from unittest import mock

from crossbench import path as pth
from crossbench.browsers.browser import Browser
from crossbench.env import HostEnvironment
from crossbench.plt.linux import LinuxPlatform
from crossbench.probes.frequency import FrequencyProbe
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


# TODO(crbug.com/372862708): Turn most of these into unit tests for
# CPUFrequencyMap and leave only 1-2 tests that verify the communication between
# the 2 classes.


class FrequencyProbeTestCase(CrossbenchFakeFsTestCase):
  __test__ = True

  def setUp(self):
    super().setUp()
    self.platform = LinuxPlatform()

  def test_parse_invalid_map_value(self):
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "Invalid value"):
      FrequencyProbe.from_config({"cpus": {"cpu0": "invalid"}})

  def test_parse_conflicting_wildcard(self):
    with self.assertRaisesRegex(argparse.ArgumentTypeError,
                                "should be the only key"):
      FrequencyProbe.from_config({"cpus": {"*": "max", "cpu0": "min"}})

  def test_key(self):
    key1 = FrequencyProbe.from_config({"cpus": {"cpu0": 1111}}).key
    key2 = FrequencyProbe.from_config({"cpus": {"*": 2222}}).key

    self.assertIsNotNone(key1)
    self.assertIsNotNone(key2)
    self.assertNotEqual(key1, key2)

  def test_validate_fails_due_to_missing_cpus_dir(self):
    probe = FrequencyProbe.from_config({"cpus": {"cpu0": 42}})
    # No call to self._create_cpu_dir().

    with self.assertRaisesRegex(FileNotFoundError,
                                "/sys/devices/system/cpu not found"):
      probe.validate_browser(
          mock.Mock(spec=HostEnvironment), self._create_mock_browser())

  def test_validate_fails_due_to_missing_cpu_name(self):
    probe = FrequencyProbe.from_config({"cpus": {"nonexistent-cpu": 1}})
    self._create_cpu_dir("cpu0", [1])

    with self.assertRaisesRegex(ValueError, "nonexistent-cpu"):
      probe.validate_browser(
          mock.Mock(spec=HostEnvironment), self._create_mock_browser())

  def test_validate_fails_due_to_missing_numerical_frequency(self):
    probe = FrequencyProbe.from_config({"cpus": {"cpu0": 42}})
    self._create_cpu_dir("cpu0", [1, 2])
    self._create_cpu_dir("cpu1", [42])

    with self.assertRaisesRegex(
        ValueError, r"Target frequency 42 for cpu0 not allowed in linux.*. "
        r"Available frequencies: \[1, 2\]"):
      probe.validate_browser(
          mock.Mock(spec=HostEnvironment), self._create_mock_browser())

  def test_validate_fails_due_to_missing_numerical_frequency_with_wildcard(
      self):
    probe = FrequencyProbe.from_config({"cpus": {"*": 42}})
    self._create_cpu_dir("cpu0", [1, 2])

    with self.assertRaisesRegex(
        ValueError, r"Target frequency 42 for cpu0 not allowed in linux.*. "
        r"Available frequencies: \[1, 2\]"):
      probe.validate_browser(
          mock.Mock(spec=HostEnvironment), self._create_mock_browser())

  def test_validate_succeeds_with_extremes(self):
    probe = FrequencyProbe.from_config({"cpus": {"cpu0": "max", "cpu1": "min"}})
    self._create_cpu_dir("cpu0", [1, 2])
    self._create_cpu_dir("cpu1", [1, 2])
    browser = self._create_mock_browser()

    # Implicitly asserts no exception occurs.
    probe.validate_browser(mock.Mock(spec=HostEnvironment), browser)
    frequency_map = probe.cpu_frequency_map.get_target_frequencies(
        browser.platform)

    self.assertDictEqual(
        dict(frequency_map), {
            pth.AnyPosixPath("/sys/devices/system/cpu/cpu0/cpufreq"): 2,
            pth.AnyPosixPath("/sys/devices/system/cpu/cpu1/cpufreq"): 1,
        })


  def test_validate_succeeds_without_wildcard(self):
    probe = FrequencyProbe.from_config(
        {"cpus": {
            "cpu0": 2,
            "cpu1": 2,
            "cpu2": 2
        }})
    # Use different orders to stress the parsing logic.
    self._create_cpu_dir("cpu0", [2, 1, 3])
    self._create_cpu_dir("cpu1", [1, 2, 3])
    self._create_cpu_dir("cpu2", [1, 3, 2])
    self._create_cpu_dir("cpu3", [42, 42, 42])
    self._create_cpu_dir("cpu4", [42, 42, 42])
    browser = self._create_mock_browser()

    # Implicitly asserts no exception occurs.
    probe.validate_browser(mock.Mock(spec=HostEnvironment), browser)
    frequency_map = probe.cpu_frequency_map.get_target_frequencies(
        browser.platform)

    self.assertDictEqual(
        dict(frequency_map), {
            pth.AnyPosixPath("/sys/devices/system/cpu/cpu0/cpufreq"): 2,
            pth.AnyPosixPath("/sys/devices/system/cpu/cpu1/cpufreq"): 2,
            pth.AnyPosixPath("/sys/devices/system/cpu/cpu2/cpufreq"): 2,
        })

  def test_validate_succeeds_with_wildcard(self):
    probe = FrequencyProbe.from_config({"cpus": {"*": 2}})
    # Use different orders to stress the parsing logic.
    self._create_cpu_dir("cpu0", [2, 1, 3])
    self._create_cpu_dir("cpu1", [1, 2, 3])
    self._create_cpu_dir("cpu2", [1, 3, 2])
    browser = self._create_mock_browser()

    # Implicitly asserts no exception occurs.
    probe.validate_browser(mock.Mock(spec=HostEnvironment), browser)
    frequency_map = probe.cpu_frequency_map.get_target_frequencies(
        browser.platform)

    self.assertDictEqual(
        dict(frequency_map), {
            pth.AnyPosixPath("/sys/devices/system/cpu/cpu0/cpufreq"): 2,
            pth.AnyPosixPath("/sys/devices/system/cpu/cpu1/cpufreq"): 2,
            pth.AnyPosixPath("/sys/devices/system/cpu/cpu2/cpufreq"): 2,
        })

  def test_validate_succeeds_for_empty_configs(self):
    browser = self._create_mock_browser()
    self._create_cpu_dir("cpu0", [1, 2, 3])

    FrequencyProbe.from_config({}).validate_browser(
        mock.Mock(spec=HostEnvironment), browser)
    FrequencyProbe.from_config({
        "cpus": {},
    }).validate_browser(mock.Mock(spec=HostEnvironment), browser)

  def test_validate_string_wildcard(self):
    probe = FrequencyProbe.from_config({"cpus": "max"})
    self._create_cpu_dir("cpu0", [1, 2, 3])
    self._create_cpu_dir("cpu1", [1, 2, 3])
    browser = self._create_mock_browser()

    # Implicitly asserts no exception occurs.
    probe.validate_browser(mock.Mock(spec=HostEnvironment), browser)
    frequency_map = probe.cpu_frequency_map.get_target_frequencies(
        browser.platform)

    self.assertDictEqual(
        dict(frequency_map), {
            pth.AnyPosixPath("/sys/devices/system/cpu/cpu0/cpufreq"): 3,
            pth.AnyPosixPath("/sys/devices/system/cpu/cpu1/cpufreq"): 3,
        })

  def _create_mock_browser(self):
    mock_browser = mock.Mock(spec=Browser)
    mock_browser.platform = self.platform
    return mock_browser

  def _create_cpu_dir(self, cpu_name: str, available_frequencies: List[int]):
    cpu_dir = pth.AnyPosixPath(f"/sys/devices/system/cpu/{cpu_name}/cpufreq")
    self.platform.mkdir(cpu_dir, parents=True, exist_ok=True)
    self.platform.set_file_contents(
        cpu_dir / "scaling_available_frequencies",
        " ".join(map(str, available_frequencies)) + "\n")
    self.platform.set_file_contents(cpu_dir / "scaling_min_freq",
                                    str(min(available_frequencies)) + "\n")
    self.platform.set_file_contents(cpu_dir / "scaling_max_freq",
                                    str(max(available_frequencies)) + "\n")

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
