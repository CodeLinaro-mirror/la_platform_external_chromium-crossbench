# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses

from crossbench.action_runner.action.action import Action


@dataclasses.dataclass(frozen=True, eq=False)
class BondAction(Action):
  """
  Base class for all actions that use the bond API exposed on ActionRunner.bond.
  """
