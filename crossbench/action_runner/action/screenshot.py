# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
from typing import ClassVar

from typing_extensions import override

from crossbench.action_runner.action.action_type import ActionType
from crossbench.action_runner.action.base_probe import BaseProbeAction


# Left here for backwards compatibility.
# New probe actions should not have individual class implementations.
# They should just be used as ProbeActions directly.
@dataclasses.dataclass(frozen=True, eq=False)
class ScreenshotAction(BaseProbeAction):
  TYPE: ClassVar[ActionType] = ActionType.SCREENSHOT
  PROBE: ClassVar[str] = "screenshot"

  @property
  @override
  def probe(self) -> str:
    return self.PROBE
