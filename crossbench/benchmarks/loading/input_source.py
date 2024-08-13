# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import enum
from typing import Any, Type, TypeVar

from crossbench.config import ConfigEnum


@enum.unique
class InputSource(ConfigEnum):
  JS: "InputSource" = (
      "js", "Inject a script into the webpage to simulate the action.")
  TOUCH: "InputSource" = ("touch", "Use the touchscreen to perform the action")
  MOUSE: "InputSource" = ("mouse", "Use the mouse to perform the action")
