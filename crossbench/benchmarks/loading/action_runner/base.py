# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Iterable

from crossbench import exception

if TYPE_CHECKING:
  from crossbench.benchmarks.loading import action as i_action
  from crossbench.benchmarks.loading.page_config import ActionBlock
  from crossbench.runner.run import Run


class ActionNotImplementedError(NotImplementedError):

  def __init__(self, runner: ActionRunner, action: i_action.Action) -> None:
    self.runner = runner
    self.action = action
    message = (f"{str(action.TYPE).capitalize()}-action "
               "not implemented in {type(runner).__name__}")
    super().__init__(message)


class ActionRunner(abc.ABC):

  def run_blocks(self, run: Run, action_blocks: Iterable[ActionBlock]):
    index = 0
    for block in action_blocks:
      index += 1
      with exception.annotate(f"Running block {index}: {block.label}"):
        for action in block.actions:
          action.run_with(run, self)

  def wait(self, run: Run, action: i_action.WaitAction) -> None:
    with run.actions("WaitAction", measure=False) as actions:
      actions.wait(action.duration)

  def js(self, run: Run, action: i_action.JsAction) -> None:
    with run.actions("JS", measure=False) as actions:
      actions.js(action.script, action.timeout)

  def scroll(self, run: Run, action: i_action.ScrollAction) -> None:
    raise ActionNotImplementedError(self, action)

  def get(self, run: Run, action: i_action.GetAction) -> None:
    raise ActionNotImplementedError(self, action)

  def click(self, run: Run, action: i_action.ClickAction) -> None:
    raise ActionNotImplementedError(self, action)

  def tap(self, run: Run, action: i_action.TapAction) -> None:
    raise ActionNotImplementedError(self, action)

  def swipe(self, run: Run, action: i_action.SwipeAction) -> None:
    raise ActionNotImplementedError(self, action)

  def wait_for_element(self, run: Run,
                       action: i_action.WaitForElementAction) -> None:
    raise ActionNotImplementedError(self, action)

  def inject_new_document_script(
      self, run: Run, action: i_action.InjectNewDocumentScriptAction) -> None:
    raise ActionNotImplementedError(self, action)
