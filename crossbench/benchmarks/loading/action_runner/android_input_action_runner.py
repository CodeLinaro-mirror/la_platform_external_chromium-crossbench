# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
import datetime as dt
import re
import time
from typing import Optional, Tuple

from crossbench.benchmarks.loading import action as i_action
from crossbench.benchmarks.loading.action_runner.basic_action_runner import \
  BasicActionRunner
from crossbench.benchmarks.loading.point import Point
from crossbench.browsers.attributes import BrowserAttributes
from crossbench.runner.actions import Actions
from crossbench.runner.run import Run


@dataclasses.dataclass(frozen=True)
# Represents a rectangular section of the device's display.
class DisplayRectangle:
  # The offset in pixels of the left edge of the rectangle from the left
  # edge of the screen.
  left: int
  # The offset in pixels of the right edge of the rectangle from the left
  # edge of the screen.
  right: int
  # The offset in pixels of the top edge of the rectangle from the top edge
  # of the screen.
  top: int
  # The offset in pixels of the bottom edge of the rectangle from the top
  # edge of the screen.
  bottom: int


class AndroidInputActionRunner(BasicActionRunner):

  # Represents the position of the chrome main window relative to the entire
  # screen as reported by Android window manager.
  _chrome_window_bounds: Optional[DisplayRectangle] = None

  _BOUNDS_RE = re.compile(
      r"mAppBounds=Rect\((?P<left>\d+), (?P<top>\d+) - (?P<right>\d+),"
      r" (?P<bottom>\d+)\)")

  def click_touch(self, run: Run, action: i_action.ClickAction) -> None:
    self._click_impl(run, action, False)

  def click_mouse(self, run: Run, action: i_action.ClickAction) -> None:
    self._click_impl(run, action, True)

  def swipe(self, run: Run, action: i_action.SwipeAction) -> None:
    with run.actions("SwipeAction", measure=False):
      x1 = str(action.start_x)
      y1 = str(action.start_y)
      x2 = str(action.end_x)
      y2 = str(action.end_y)
      dur_ms = str(action.duration // dt.timedelta(milliseconds=1))
      run.browser.platform.sh("input", "swipe", x1, y1, x2, y2, dur_ms)

  def _init_chrome_window_size_if_necessary(self, run: Run,
                                            actions: Actions) -> None:
    # If the chrome window position has not yet been found,
    # initialize it now.
    # Note: this assumes the chrome app will not be moved or resized during
    # the test.
    if self._chrome_window_bounds is None:
      self._chrome_window_bounds = self._find_chrome_window_size(run, actions)

  # Returns the name of the browser's main window as reported by android's
  # window manager.
  def _get_browser_window_name(self,
                               browser_attributes: BrowserAttributes) -> str:
    if browser_attributes.is_chrome:
      return "chrome.Main"

    raise RuntimeError("Unsupported browser for android action runner.")

  def _find_chrome_window_size(self, run: Run,
                               actions: Actions) -> DisplayRectangle:
    # Find the chrome app window position by dumping the android app window
    # list.
    #
    # Chrome's main view is always called 'chrome.Main' and is followed by the
    # configuration for that window.
    #
    # The mAppBounds config of the chrome.Main window contains the dimensions
    # for the visible part of the current chrome window formatted like this for
    # a 800 height by 480 width window:
    #
    # mAppBounds=Rect(0, 0 - 480, 800)
    browser_main_window_name = self._get_browser_window_name(
        run.browser.attributes)

    raw_window_config = run.browser.platform.sh_stdout(
        "dumpsys",
        "window",
        "windows",
        "|",
        "grep",
        "-E",
        "-A100",
        browser_main_window_name,
    )
    match = self._BOUNDS_RE.search(raw_window_config)
    if not match:
      raise RuntimeError("Could not find chrome window bounds")

    window_bounds = DisplayRectangle(
        int(match["left"]),
        int(match["right"]),
        int(match["top"]),
        int(match["bottom"]),
    )

    # On Android there may be a system added border from the top of the app view
    # that is included in the mAppBounds rectangle dimensions. Calculate the
    # height of this border using the difference between the height reported by
    # chrome and the height reported by android.
    inner_height = actions.js(
        "return window.innerHeight;") * self._get_actual_pixel_ratio(
            actions, window_bounds)
    top_border_height = (window_bounds.bottom -
                         window_bounds.top) - inner_height

    return DisplayRectangle(window_bounds.left, window_bounds.right,
                            window_bounds.top + top_border_height,
                            window_bounds.bottom)

  def _get_actual_pixel_ratio(
      self,
      actions: Actions,
      window_bounds: Optional[DisplayRectangle] = None) -> float:
    # On android, clank does not report the correct window.devicePixelRatio
    # when a page is zoomed.
    # Zoom can happen automatically on load with pages that force a certain
    # viewport width (such as speedometer), so calculate the ratio manually.
    # Note: this calculation assumes there are no system borders on the side of
    # the chrome window.

    if window_bounds is None:
      window_bounds = self._chrome_window_bounds

    inner_width = actions.js("return window.innerWidth;")

    return float((window_bounds.right - window_bounds.left) / inner_width)

  # Given a selector, return the bounding rectangle for the element in terms of
  # the device's native pixel count.
  def _get_element_bounding_rect(self, actions: Actions,
                                 selector: str) -> Optional[DisplayRectangle]:

    selector, script = self.get_selector_script(selector)

    script += """
            if(!element) return [false, 0, 0, 0, 0];

            const rect = element.getBoundingClientRect();
            return [
              true,
              rect.left,
              rect.right,
              rect.top,
              rect.bottom,
            ];
    """
    (
        found_element,
        element_left,
        element_right,
        element_top,
        element_bottom,
    ) = actions.js(
        script,
        arguments=[selector],
    )

    if not found_element:
      return None

    ratio = self._get_actual_pixel_ratio(actions)

    # Adjust all the browser reported pixel values by the calculated ratio.
    element_left *= ratio
    element_right *= ratio
    element_top *= ratio
    element_bottom *= ratio

    # Adjust the left and right coordinates of the element by the window
    # position in android.
    window_bounds = self._chrome_window_bounds
    element_left += window_bounds.left
    element_right += window_bounds.left

    element_top += self._chrome_window_bounds.top
    element_bottom += self._chrome_window_bounds.top

    return DisplayRectangle(element_left, element_right, element_top,
                            element_bottom)

  # Given a selector, find the center point of the element in terms of the
  # device's native pixel count.
  def _get_element_centerpoint(self, run: Run, actions: Actions,
                               selector: str) -> Optional[Point]:
    self._init_chrome_window_size_if_necessary(run, actions)

    rect: Optional[DisplayRectangle] = self._get_element_bounding_rect(
        actions, selector)

    if not rect:
      return None

    # Find the center of the element.
    x = (rect.left + rect.right) / 2
    y = (rect.top + rect.bottom) / 2

    return Point(round(x), round(y))

  def _scroll_element_into_view(self, actions: Actions, selector: str) -> bool:
    selector, script = self.get_selector_script(
        selector,
        check_element_exists=True,
        scroll_into_view=True,
        return_on_success=True)

    return actions.js(script, arguments=[selector])

  def _click_impl(self, run: Run, action: i_action.ClickAction,
                  use_mouse: bool) -> None:
    with run.actions("ClickAction", measure=False) as actions:
      if action.scroll_into_view and not self._scroll_element_into_view(
          actions, action.selector) and action.required:
        raise RuntimeError(
            f"Could not find matching DOM element: {repr(action.selector)}")

      coordinates = self._get_element_centerpoint(run, actions, action.selector)

      if not coordinates:
        if action.required:
          raise RuntimeError(
              f"Could not find matching DOM element: {repr(action.selector)}")
        return

      mouse_str: str = ""

      if use_mouse:
        mouse_str = "mouse"

      run.browser.platform.sh(
          f"input {mouse_str} tap {str(coordinates.x)} {str(coordinates.y)}",
          shell=True)
