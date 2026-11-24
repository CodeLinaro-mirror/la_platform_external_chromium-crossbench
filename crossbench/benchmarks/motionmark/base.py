# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
from typing import TYPE_CHECKING, override

from crossbench import config
from crossbench.benchmarks.base import PressBenchmark
from crossbench.device_config import RequiredDeviceConfig

if TYPE_CHECKING:
  from crossbench import path as pth
  from crossbench.plt.base import Platform
  from crossbench.runner.runner import Runner


class MotionMarkBenchmark(PressBenchmark):
  @classmethod
  @override
  def short_base_name(cls) -> str:
    return "mm"

  @classmethod
  @override
  def base_name(cls) -> str:
    return "motionmark"

  @classmethod
  def device_config_path(cls) -> pth.LocalPath:
    return (
      config.config_dir() / "benchmark" / "motionmark" / "device_config.hjson"
    )

  @override
  def required_device_config(self, platform: Platform) -> RequiredDeviceConfig:
    del platform
    return RequiredDeviceConfig.parse(self.device_config_path())

  @override
  def setup(self, runner: Runner) -> None:
    # According to the official MotionMark documentation
    # (https://browserbench.org/MotionMark1.3/about.html):
    # "To compare browser scores across browsers,
    # be sure to set the screen refresh rate to 60Hz."
    super().setup(runner)
    for platform in runner.platforms:
      try:
        platform.set_display_refresh_rate(60)
      except NotImplementedError:
        logging.warning(
          "Failed to automatically apply 60Hz refresh rate on %s. "
          "Setting the screen refresh rate manually to 60Hz is strongly "
          "recommended for fair cross-platform and cross-browser comparison.",
          platform,
        )

  @override
  def teardown(self, runner: Runner) -> None:
    for platform in runner.platforms:
      platform.reset_display_refresh_rate()
    super().teardown(runner)
