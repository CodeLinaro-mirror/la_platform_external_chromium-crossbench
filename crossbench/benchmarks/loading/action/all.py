# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import Tuple, Type

from crossbench.benchmarks.loading.action.action import ACTIONS, Action
from crossbench.benchmarks.loading.action.click import ClickAction
from crossbench.benchmarks.loading.action.get import GetAction
from crossbench.benchmarks.loading.action.inject_new_document_script import \
    InjectNewDocumentScriptAction
from crossbench.benchmarks.loading.action.js import JsAction
from crossbench.benchmarks.loading.action.screenshot import ScreenshotAction
from crossbench.benchmarks.loading.action.scroll import ScrollAction
from crossbench.benchmarks.loading.action.swipe import SwipeAction
from crossbench.benchmarks.loading.action.switch_tab import SwitchTabAction
from crossbench.benchmarks.loading.action.text_input import TextInputAction
from crossbench.benchmarks.loading.action.wait import WaitAction
from crossbench.benchmarks.loading.action.wait_for_element import \
    WaitForElementAction
from crossbench.benchmarks.loading.action.wait_for_ready_state import \
    WaitForReadyStateAction

ACTIONS_TUPLE: Tuple[Type[Action], ...] = (
    ClickAction,
    GetAction,
    InjectNewDocumentScriptAction,
    JsAction,
    ScreenshotAction,
    ScrollAction,
    SwipeAction,
    SwitchTabAction,
    TextInputAction,
    WaitAction,
    WaitForElementAction,
    WaitForReadyStateAction,
)
for action_cls in ACTIONS_TUPLE:
  ACTIONS[action_cls.TYPE] = action_cls

assert len(ACTIONS_TUPLE) == len(ACTIONS), "Non unique Action.TYPE present"
