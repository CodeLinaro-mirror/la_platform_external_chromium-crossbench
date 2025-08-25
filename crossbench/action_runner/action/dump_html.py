# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING

from crossbench.action_runner.action.action import ACTION_TIMEOUT
from crossbench.action_runner.action.action_type import ActionType
from crossbench.action_runner.action.probe import ProbeAction

if TYPE_CHECKING:
  import datetime as dt


# Left here for backwards compatibility.
# New probe actions should not have individual class implementations.
# They should just be used as ProbeActions directly.
class DumpHtmlAction(ProbeAction):
  TYPE: ActionType = ActionType.DUMP_HTML

  def __init__(self,
               timeout: dt.timedelta = ACTION_TIMEOUT,
               index: int = 0) -> None:
    super().__init__(probe="dump_html", kwargs={}, timeout=timeout, index=index)
