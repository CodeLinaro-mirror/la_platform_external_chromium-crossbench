# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Iterable, Optional

from crossbench.benchmarks.loading.input_source import InputSource

from crossbench import exception

if TYPE_CHECKING:
  from crossbench.benchmarks.loading import action as i_action
  from crossbench.benchmarks.loading.page_config import ActionBlock
  from crossbench.benchmarks.loading.point import Point
  from crossbench.runner.run import Run


class ActionNotImplementedError(NotImplementedError):

  def __init__(self,
               runner: ActionRunner,
               action: i_action.Action,
               msg_context: str = "") -> None:
    self.runner = runner
    self.action = action

    if msg_context:
      msg_context = ". Context: " + msg_context

    message = (f"{str(action.TYPE).capitalize()}-action "
               f"not implemented in {type(runner).__name__}{msg_context}")
    super().__init__(message)


class InputSourceNotImplementedError(ActionNotImplementedError):

  def __init__(self, runner: ActionRunner, action: i_action.Action,
               input_source: InputSource) -> None:
    input_source_message = f"Source: '{input_source}' not implemented"
    super().__init__(runner, action, input_source_message)


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

  def click(self, run: Run, action: i_action.ClickAction) -> None:
    input_source = action.input_source
    if input_source is InputSource.JS:
      self.click_js(run, action)
    elif input_source is InputSource.TOUCH:
      self.click_touch(run, action)
    elif input_source is InputSource.MOUSE:
      self.click_mouse(run, action)
    else:
      raise RuntimeError(f"Unsupported input source: '{input_source}'")

  def scroll(self, run: Run, action: i_action.ScrollAction) -> None:
    input_source = action.input_source
    if input_source is InputSource.JS:
      self.scroll_js(run, action)
    elif input_source is InputSource.TOUCH:
      self.scroll_touch(run, action)
    elif input_source is InputSource.MOUSE:
      self.scroll_mouse(run, action)
    else:
      raise RuntimeError(f"Unsupported input source: '{input_source}'")

  def get(self, run: Run, action: i_action.GetAction) -> None:
    raise ActionNotImplementedError(self, action)

  def click_js(self, run: Run, action: i_action.ClickAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def click_touch(self, run: Run, action: i_action.ClickAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def click_mouse(self, run: Run, action: i_action.ClickAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def scroll_js(self, run: Run, action: i_action.ScrollAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def scroll_touch(self, run: Run, action: i_action.ScrollAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def scroll_mouse(self, run: Run, action: i_action.ScrollAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def swipe(self, run: Run, action: i_action.SwipeAction) -> None:
    raise ActionNotImplementedError(self, action)

  def wait_for_element(self, run: Run,
                       action: i_action.WaitForElementAction) -> None:
    raise ActionNotImplementedError(self, action)

  def inject_new_document_script(
      self, run: Run, action: i_action.InjectNewDocumentScriptAction) -> None:
    raise ActionNotImplementedError(self, action)
