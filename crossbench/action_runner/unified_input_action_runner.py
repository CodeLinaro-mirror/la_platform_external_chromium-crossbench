# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Final

from crossbench.action_runner.base import ActionRunner
from crossbench.action_runner.input_events import InputEvent, KeyEvent, \
    WaitEvent
from crossbench.action_runner.keyboard_layout import US_KEYBOARD_LAYOUT

if TYPE_CHECKING:
  from crossbench.action_runner.action import all as i_action


class UnifiedInputActionRunner(ActionRunner):
  """
    ActionRunner implementation that translates abstract actions
    into sequences of InputEvent objects, and injects them via the
    platform level.
    """

  # Relative timing weights used to distribute `action.duration` across the
  # various phases of keyboard input. Each character receives a total weight of
  # 10 units, ensuring uniform typing speed across characters.
  #
  # Example: For a typing rate of 200ms per character (5 chars in 1 second):
  #   - Unshifted character ('a'):
  #       KeyDown(KeyA) -> 80ms (40%) -> KeyUp(KeyA) -> 120ms (60%)
  #   - Shifted character ('A'):
  #       KeyDown(ShiftLeft) -> 20ms (10%)
  #       KeyDown(KeyA)      -> 60ms (30%)
  #       KeyUp(KeyA)        -> 20ms (10%)
  #       KeyUp(ShiftLeft)   -> 100ms (50%)
  KEY_HOLD_WEIGHT: Final[int] = 4
  KEY_GAP_WEIGHT: Final[int] = 6

  SHIFT_PRE_DWELL_WEIGHT: Final[int] = 1
  SHIFT_KEY_HOLD_WEIGHT: Final[int] = 3
  SHIFT_POST_DWELL_WEIGHT: Final[int] = 1
  SHIFT_GAP_WEIGHT: Final[int] = 5

  def click_touch(self, action: i_action.ClickAction) -> None:
    # TODO(b/553272919): implement
    del action

  def click_mouse(self, action: i_action.ClickAction) -> None:
    # TODO(b/553272919): implement
    del action

  def scroll_touch(self, action: i_action.ScrollAction) -> None:
    # TODO(b/553272919): implement
    del action

  def swipe(self, action: i_action.SwipeAction) -> None:
    # TODO(b/553272919): implement
    del action

  def _text_to_weighted_events(self, text: str) -> list[KeyEvent | int]:
    events: list[KeyEvent | int] = []
    for char in text:
      mapping = US_KEYBOARD_LAYOUT.get(char)
      if not mapping:
        raise ValueError(f"Character {char!r} is not supported "
                         "in the standard US keyboard layout.")

      if mapping.has_shift:
        events.append(KeyEvent("ShiftLeft", is_down=True))
        events.append(self.SHIFT_PRE_DWELL_WEIGHT)
        events.append(KeyEvent(mapping.code, is_down=True))
        events.append(self.SHIFT_KEY_HOLD_WEIGHT)
        events.append(KeyEvent(mapping.code, is_down=False))
        events.append(self.SHIFT_POST_DWELL_WEIGHT)
        events.append(KeyEvent("ShiftLeft", is_down=False))
        events.append(self.SHIFT_GAP_WEIGHT)
      else:
        events.append(KeyEvent(mapping.code, is_down=True))
        events.append(self.KEY_HOLD_WEIGHT)
        events.append(KeyEvent(mapping.code, is_down=False))
        events.append(self.KEY_GAP_WEIGHT)

    return events

  def text_input_keyboard(self, action: i_action.TextInputAction) -> None:
    events_with_weights: list[KeyEvent | int] = []
    if action.text:
      events_with_weights.extend(self._text_to_weighted_events(action.text))
    elif action.keyevent:
      events_with_weights.extend([
          KeyEvent(key_code=action.keyevent, is_down=True),
          self.KEY_HOLD_WEIGHT,
          KeyEvent(key_code=action.keyevent, is_down=False),
          self.KEY_GAP_WEIGHT,
      ])

    if not events_with_weights:
      return

    device_name = action.source_device or ""

    if not action.duration:
      input_events = [e for e in events_with_weights if isinstance(e, KeyEvent)]
      self.browser_platform.inject_input_events(device_name, input_events)
      return

    total_weight = sum(w for w in events_with_weights if isinstance(w, int))
    total_duration_us = int(action.duration.total_seconds() * 1_000_000)
    cumulative_weight = 0
    previous_cumulative_us = 0

    timed_events: list[InputEvent] = []
    for item in events_with_weights:
      if isinstance(item, KeyEvent):
        timed_events.append(item)
      else:
        cumulative_weight += item
        target_cumulative_us = (total_duration_us *
                                cumulative_weight) // total_weight
        wait_us = target_cumulative_us - previous_cumulative_us
        previous_cumulative_us = target_cumulative_us
        if wait_us > 0:
          timed_events.append(
              WaitEvent(duration=dt.timedelta(microseconds=wait_us)))

    self.browser_platform.inject_input_events(device_name, timed_events)
