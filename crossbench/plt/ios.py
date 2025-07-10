# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING

from crossbench.plt.device_info import DeviceInfo

if TYPE_CHECKING:
  from crossbench.plt.base import Platform

pattern: re.Pattern[str] = re.compile(
    r"(?P<name>[^\(\)]+) \((?P<version>[0-9\.]+)\) (- Connecting )?"
    r"\((?P<udid>[0-9A-Z-]+)\)")


@dataclasses.dataclass(frozen=True)
class IOSDeviceInfo(DeviceInfo):
  version: str = ""

  @property
  def udid(self) -> str:
    return self.device_id

  def __str__(self) -> str:
    return f"{self.name} ({self.version}) ({self.udid})"


def ios_devices(platform: Platform,
                show_all: bool = False) -> dict[str, IOSDeviceInfo]:
  output = platform.sh_stdout("xcrun", "xctrace", "list", "devices")
  category_index = 0
  results: dict[str, IOSDeviceInfo] = {}
  for line in output.splitlines():
    if line.startswith("== "):
      category_index += 1
      continue
    if category_index > 1 and not show_all:
      return results

    for match in pattern.finditer(line):
      device = IOSDeviceInfo(
          match.group("udid"), match.group("name"), match.group("version"))
      if device.udid in results:
        raise ValueError("Invalid UDID")
      results[device.udid] = device
  return results
