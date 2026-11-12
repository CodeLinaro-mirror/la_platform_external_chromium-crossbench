# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
from typing import ClassVar, Final

from crossbench.action_runner.virtual_device.pointing import (
  PointingVirtualDeviceConfig,
)
from crossbench.action_runner.virtual_device.virtual_device_type import (
  VirtualDeviceType,
)

DEFAULT_TOUCH_POLLING_RATE_HZ: Final[int] = 120


@dataclasses.dataclass(frozen=True)
class TouchscreenVirtualDeviceConfig(PointingVirtualDeviceConfig):
  TYPE: ClassVar[VirtualDeviceType] = VirtualDeviceType.TOUCHSCREEN
  DEFAULT_POLLING_RATE_HZ: ClassVar[int] = DEFAULT_TOUCH_POLLING_RATE_HZ
  polling_rate_hz: int = DEFAULT_TOUCH_POLLING_RATE_HZ
