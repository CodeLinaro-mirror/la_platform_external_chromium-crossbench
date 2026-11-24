# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from unittest import mock

from crossbench.benchmarks.motionmark.base import MotionMarkBenchmark
from crossbench.benchmarks.motionmark.motionmark_1_3 import (
  MotionMark13Benchmark,
  MotionMark13Story,
)
from crossbench.device_config import (
  DeviceConfigRequirements,
  DeviceConfigValueError,
  RequiredDeviceConfig,
  RequiredDeviceConfigMode,
  check_device_config,
)
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.mock_helper import (
  AndroidAdbMockPlatform,
  LinuxMockPlatform,
)


class MotionMarkRequiredDeviceConfigTestCase(CrossbenchFakeFsTestCase):
  """Tests for the device config requirements shipped with MotionMark."""

  def setUp(self) -> None:
    super().setUp()
    self.config_path = MotionMarkBenchmark.device_config_path()
    self.fs.add_real_file(self.config_path)

  def android_requirements(self) -> DeviceConfigRequirements:
    return RequiredDeviceConfig.parse(self.config_path).platforms["android"]

  def check(self, accelerometer_rotation: str, user_rotation: str) -> None:
    """Checks a device reporting the given rotation settings."""
    actual = {
      "settings": {
        "system": {
          "accelerometer_rotation": accelerometer_rotation,
          "user_rotation": user_rotation,
        }
      }
    }
    check_device_config(
      self.android_requirements(), actual, RequiredDeviceConfigMode.THROW
    )

  def test_benchmark_requires_shipped_config(self) -> None:
    benchmark = MotionMark13Benchmark(
      MotionMark13Story.from_names(["Multiply"])
    )
    platform = AndroidAdbMockPlatform(
      LinuxMockPlatform(), "emulator-5554", adb=mock.MagicMock()
    )
    self.assertEqual(
      benchmark.required_device_config(platform),
      RequiredDeviceConfig.parse(self.config_path),
    )

  def test_targets_locked_landscape(self) -> None:
    targets = {req.key_path: req.target for req in self.android_requirements()}
    self.assertEqual(
      targets,
      {
        ("settings", "system", "accelerometer_rotation"): "0",
        ("settings", "system", "user_rotation"): "1",
      },
    )

  def test_accepts_locked_landscape(self) -> None:
    self.check(accelerometer_rotation="0", user_rotation="1")

  def test_rejects_auto_rotation(self) -> None:
    with self.assertRaisesRegex(
      DeviceConfigValueError, "accelerometer_rotation"
    ):
      self.check(accelerometer_rotation="1", user_rotation="1")

  def test_rejects_portrait(self) -> None:
    with self.assertRaisesRegex(DeviceConfigValueError, "user_rotation"):
      self.check(accelerometer_rotation="0", user_rotation="0")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
