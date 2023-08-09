# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Union


@dataclasses.dataclass(frozen=True)
class Timing:
  cool_down_time: dt.timedelta = dt.timedelta(seconds=1)
  unit: dt.timedelta = dt.timedelta(seconds=1)
  run_timeout: dt.timedelta = dt.timedelta()

  def __post_init__(self) -> None:
    if self.cool_down_time.total_seconds() < 0:
      raise ValueError(
          f"Timing.cool_down_time must be >= 0, but got: {self.cool_down_time}")
    if self.unit.total_seconds() <= 0:
      raise ValueError(f"Timing.unit must be > 0, but got {self.unit}")
    if self.run_timeout.total_seconds() < 0:
      raise ValueError(
          f"Timing.run_timeout, must be >= 0, but got {self.run_timeout}")

  def units(self, time: Union[float, int, dt.timedelta]) -> float:
    if isinstance(time, dt.timedelta):
      seconds = time.total_seconds()
    else:
      seconds = time
    if seconds < 0:
      raise ValueError(f"Unexpected negative time: {seconds}s")
    return seconds / self.unit.total_seconds()

  def timedelta(self,
                time_units: Union[float, int, dt.timedelta],
                absolute: bool = False) -> dt.timedelta:
    if absolute:
      if isinstance(time_units, dt.timedelta):
        return time_units
      return dt.timedelta(seconds=time_units)
    if isinstance(time_units, dt.timedelta):
      time_units = time_units.total_seconds()
    assert isinstance(time_units, (float, int))
    if time_units < 0:
      raise ValueError(f"Time-units must be >= 0, but got {time_units}")
    return time_units * self.unit
