# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  import datetime as dt


@dataclasses.dataclass(frozen=True)
class InputEvent:
  pass


@dataclasses.dataclass(frozen=True)
class WaitEvent(InputEvent):
  duration: dt.timedelta


@dataclasses.dataclass(frozen=True)
class KeyEvent(InputEvent):
  # key_code represents the physical key using the W3C KeyboardEvent.code
  # specification (e.g. "KeyA", "Space", "ShiftLeft").
  key_code: str
  is_down: bool
