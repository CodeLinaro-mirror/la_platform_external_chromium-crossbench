# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import datetime as dt
import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from crossbench import compat

if TYPE_CHECKING:
  from crossbench.runner import Run
  from crossbench.stories import Story
  from crossbench import helper


class Scroll(compat.StrEnum):
  UP = "up"
  DOWN = "down"


class ButtonClick(compat.StrEnum):
  LEFT = "left"
  RIGHT = "right"
  MIDDLE = "middle"


class ActionType(compat.StrEnum):
  GET = "get"
  WAIT = "wait"
  SCROLL = "scroll"
  CLICK = "click"


class Action(abc.ABC):
  TYPE: ActionType = ActionType.GET

  timeout: float
  _story: Story

  _EXCEPTION_BASE_STR = "Not valid action for scenario: "

  def __init__(self,
               value: Optional[str] = None,
               duration: dt.timedelta = dt.timedelta()):
    self.value = value
    assert isinstance(duration, dt.timedelta)
    self._duration = duration

  @property
  def duration(self) -> dt.timedelta:
    return self._duration

  @abc.abstractmethod
  def run(self, run: Run, story: Story) -> None:
    pass

  @abc.abstractmethod
  def _validate_action(self) -> None:
    pass

  @abc.abstractmethod
  def details_json(self) -> helper.JsonDict:
    pass


class ReadyState(compat.StrEnum):
  """See https://developer.mozilla.org/en-US/docs/Web/API/Document/readyState"""
  ANY = "any"
  LOADING = "loading"
  INTERACTIVE = "interactive"
  COMPLETE = "complete"


class GetAction(Action):
  TYPE: ActionType = ActionType.GET

  def __init__(self,
               value: Optional[str] = None,
               duration: dt.timedelta = dt.timedelta(),
               ready_state: ReadyState = ReadyState.ANY):
    self._ready_state = ready_state
    super().__init__(value, duration)

  def run(self, run: Run, story: Story) -> None:
    self._story = story
    self._validate_action()
    with run.actions("GetAction") as action:
      assert self.value
      action.show_url(self.value)
      if self._ready_state == ReadyState.ANY:
        return
      action.wait_js_condition(
          f"return document.readyState === '{self._ready_state}'", 0.5, 15)

  def _validate_action(self) -> None:
    if not self.value:
      raise ValueError(self._EXCEPTION_BASE_STR +
                       f"{self._story.name}. Argument 'value' is not provided")

  def details_json(self) -> helper.JsonDict:
    return {"action": str(self.TYPE), "value": self.value}


class WaitAction(Action):
  TYPE: ActionType = ActionType.WAIT

  def run(self, run: Run, story: Story) -> None:
    self._story = story
    self._validate_action()
    run.runner.wait(self.duration)

  def _validate_action(self) -> None:
    if not self.duration:
      raise ValueError(
          self._EXCEPTION_BASE_STR +
          f"{self._story.name}. Argument 'duration' is not provided")

  def details_json(self) -> helper.JsonDict:
    return {"action": str(self.TYPE), "duration": self.duration.total_seconds()}


class ScrollAction(Action):
  TYPE: ActionType = ActionType.SCROLL

  def run(self, run: Run, story: Story) -> None:
    self._story = story
    self._validate_action()
    time_end = time.time() + self.duration.total_seconds()
    direction = 1 if self.value == Scroll.UP else -1

    start = 0
    end = direction

    while time.time() < time_end:
      # TODO: REMOVE COMMENT CODE ONCE pyautogui ALLOWED ON GOOGLE3
      # if events_source == 'js'
      run.browser.js(run.runner, f"window.scrollTo({start}, {end});")
      start = end
      end += 100
      # else :
      #   pyautogui.scroll(direction)

  def _validate_action(self) -> None:
    if not self.duration or not self.value:
      raise ValueError(
          self._EXCEPTION_BASE_STR +
          f"{self._story.name}. Argument 'duration' is not provided")

  def details_json(self) -> helper.JsonDict:
    return {
        "action": str(self.TYPE),
        "value": self.value,
        "duration": self.duration.total_seconds(),
    }


class ClickAction(Action):
  TYPE: ActionType = ActionType.CLICK

  def __init__(self,
               value: Optional[str] = None,
               duration: dt.timedelta = dt.timedelta(),
               scroll_into_view: bool = False):
    self._scroll_into_view = scroll_into_view
    super().__init__(value, duration)

  def run(self, run: Run, story: Story) -> None:
    # TODO: support more selector types.
    prefix = "xpath/"
    if self.value and self.value.startswith(prefix):
      xpath: str = self.value[len(prefix):]
      run.browser.js(
          run.runner,
          """
       let element = document.evaluate(arguments[0], document).iterateNext();
       if (arguments[1]) element.scrollIntoView()
       element.click()
       """,
          arguments=[xpath, self._scroll_into_view])
    else:
      raise NotImplementedError(f"Unsupported selector: {self.value}")

  def _validate_action(self) -> None:
    pass

  def details_json(self) -> helper.JsonDict:
    return {
        "action": str(self.TYPE),
        "value": self.value,
        "duration": self.duration.total_seconds(),
    }


ACTION_FACTORY: Dict[ActionType, Type] = {
    ActionType.GET: GetAction,
    ActionType.WAIT: WaitAction,
    ActionType.SCROLL: ScrollAction,
}
