# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import sys
from typing import Final

from .android_adb import Adb, AndroidAdbPlatform, adb_devices
from .linux import LinuxPlatform
from .macos import MacOSPlatform
from .platform import MachineArch, Platform, SubprocessError
from .win import WinPlatform


def _get_default() -> Platform:
  if sys.platform == "linux":
    return LinuxPlatform()
  if sys.platform == "darwin":
    return MacOSPlatform()
  if sys.platform == "win32":
    return WinPlatform()
  raise NotImplementedError("Unsupported Platform")


PLATFORM: Final[Platform] = _get_default()

__all__ = (
    "adb_devices",
    "Adb",
    "AndroidAdbPlatform",
    "MachineArch",
    "Platform",
    "PLATFORM",
    "SubprocessError",
)
