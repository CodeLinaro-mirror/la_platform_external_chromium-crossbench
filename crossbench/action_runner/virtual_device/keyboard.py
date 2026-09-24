# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
from typing import ClassVar

from crossbench.action_runner.virtual_device.virtual_device_config import \
    VirtualDeviceConfig
from crossbench.action_runner.virtual_device.virtual_device_type import \
    VirtualDeviceType


@dataclasses.dataclass(frozen=True)
class KeyboardVirtualDeviceConfig(VirtualDeviceConfig):
  TYPE: ClassVar[VirtualDeviceType] = VirtualDeviceType.KEYBOARD
