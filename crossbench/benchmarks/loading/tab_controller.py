# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import dataclasses

from crossbench.config import ConfigObject
from typing import Any, Dict


@dataclasses.dataclass(frozen=True)
class TabController(ConfigObject):
  multiple_tabs: bool

  @classmethod
  def load_dict(cls, config: Dict[str, Any]) -> TabController:
    raise NotImplementedError()

  @classmethod
  def loads(cls, value: str) -> TabController:
    if value == "multiple":
      return cls.multiple()
    if value == "single":
      return cls.single()
    raise argparse.ArgumentTypeError(
        'Value has to be either multiple or single')

  @classmethod
  def default(cls) -> TabController:
    return cls.single()

  @classmethod
  def multiple(cls) -> TabController:
    """
    Specify multiple_tabs as True. The given urls will be opened in multiple tabs.
    """
    return TabController(True)

  @classmethod
  def single(cls) -> TabController:
    """
    Specify multiple_tabs as False. The given urls will be opened in single tab.
    """
    return TabController(False)
