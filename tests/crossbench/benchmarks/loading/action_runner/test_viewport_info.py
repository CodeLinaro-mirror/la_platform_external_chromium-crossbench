# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import unittest

from crossbench.action_runner.display_rectangle import DisplayRectangle
from crossbench.action_runner.viewport_info import ViewportInfo
from crossbench.benchmarks.loading.point import Point
from tests import test_helper


class ViewportInfoTestCase(unittest.TestCase):

  def test_element_rect_no_element(self) -> None:
    viewport_info = ViewportInfo(
        device_pixel_ratio=1,
        window_outer_width=1920,
        window_outer_height=1080,
        window_inner_width=1920,
        window_inner_height=1080,
        screen_width=1920,
        screen_height=1080,
        screen_avail_width=1920,
        screen_avail_height=1080,
        window_offset_x=0,
        window_offset_y=0,
        element_rect=None)

    self.assertFalse(viewport_info.element_rect)

  _NO_RATIO_NO_OFFSET = ViewportInfo(
      device_pixel_ratio=1,
      window_outer_width=1920,
      window_outer_height=1080,
      window_inner_width=1920,
      window_inner_height=1080,
      screen_width=1920,
      screen_height=1080,
      screen_avail_width=1920,
      screen_avail_height=1080,
      window_offset_x=0,
      window_offset_y=0,
      element_rect=DisplayRectangle(Point(1, 2), 3, 4))

  def test_browser_viewable_no_ratios_no_offset(self) -> None:
    self.assertEqual(self._NO_RATIO_NO_OFFSET.browser_viewable,
                     DisplayRectangle(Point(0, 0), 1920, 1080))

  def test_css_to_native_no_ratio(self) -> None:
    self.assertEqual(
        self._NO_RATIO_NO_OFFSET.css_to_native_distance(1234), 1234)

  def test_element_rect_no_ratio_no_offset(self) -> None:
    self.assertEqual(self._NO_RATIO_NO_OFFSET.element_rect,
                     DisplayRectangle(Point(1, 2), 3, 4))

  _DOUBLE_RATIO_NO_OFFSET = ViewportInfo(
      device_pixel_ratio=2,
      window_outer_width=1920,
      window_outer_height=1080,
      window_inner_width=1920,
      window_inner_height=1080,
      screen_width=1920,
      screen_height=1080,
      screen_avail_width=1920,
      screen_avail_height=1080,
      window_offset_x=0,
      window_offset_y=0,
      element_rect=DisplayRectangle(Point(1, 2), 3, 4))

  def test_css_to_native_double_ratio(self) -> None:
    viewport_info = self._DOUBLE_RATIO_NO_OFFSET

    self.assertEqual(viewport_info.css_to_native_distance(100), 200)

  def test_browser_viewable_double_ratio(self) -> None:
    viewport_info = self._DOUBLE_RATIO_NO_OFFSET

    self.assertEqual(viewport_info.browser_viewable,
                     DisplayRectangle(Point(0, 0), 3840, 2160))

  def test_element_rect_double_ratio(self) -> None:
    viewport_info = self._DOUBLE_RATIO_NO_OFFSET

    self.assertEqual(viewport_info.element_rect,
                     DisplayRectangle(Point(2, 4), 6, 8))

  def test_browser_viewable_no_ratios_with_browser_window_offset(self) -> None:
    viewport_info = ViewportInfo(
        device_pixel_ratio=1,
        window_outer_width=1920,
        window_outer_height=1080,
        window_inner_width=1920,
        window_inner_height=1080,
        screen_width=1920,
        screen_height=1080,
        screen_avail_width=1920,
        screen_avail_height=1080,
        window_offset_x=10,
        window_offset_y=20,
        element_rect=None)

    self.assertEqual(viewport_info.browser_viewable,
                     DisplayRectangle(Point(10, 20), 1910, 1060))

  def test_element_rect_no_ratios_with_browser_window_offset(self) -> None:
    viewport_info = ViewportInfo(
        device_pixel_ratio=1,
        window_outer_width=1920,
        window_outer_height=1080,
        window_inner_width=1920,
        window_inner_height=1080,
        screen_width=1920,
        screen_height=1080,
        screen_avail_width=1920,
        screen_avail_height=1080,
        window_offset_x=10,
        window_offset_y=20,
        element_rect=DisplayRectangle(Point(1, 2), 3, 4))

    self.assertEqual(viewport_info.element_rect,
                     DisplayRectangle(Point(11, 22), 3, 4))

  def test_element_rect_no_ratios_with_browser_window_offset_2(self) -> None:
    viewport_info = ViewportInfo(
        device_pixel_ratio=1,
        window_outer_width=1920,
        window_outer_height=1080,
        window_inner_width=1920,
        window_inner_height=900,
        screen_width=1920,
        screen_height=1080,
        screen_avail_width=1920,
        screen_avail_height=1080,
        window_offset_x=10,
        window_offset_y=20,
        element_rect=None)

    self.assertEqual(viewport_info.browser_viewable,
                     DisplayRectangle(Point(10, 200), 1910, 880))

  def test_element_rect_no_ratios_with_browser_window_offset_3(self) -> None:
    viewport_info = ViewportInfo(
        device_pixel_ratio=1,
        window_outer_width=1920,
        window_outer_height=1080,
        window_inner_width=1920,
        window_inner_height=900,
        screen_width=1920,
        screen_height=1080,
        screen_avail_width=1920,
        screen_avail_height=1080,
        window_offset_x=10,
        window_offset_y=20,
        element_rect=DisplayRectangle(Point(1, 2), 3, 4))

    self.assertEqual(viewport_info.element_rect,
                     DisplayRectangle(Point(11, 202), 3, 4))

  def test_windowed_mode_with_toolbar_and_borders(self) -> None:
    # Simulates Android desktop / windowed mode
    viewport_info = ViewportInfo(
        device_pixel_ratio=1.77125,
        window_outer_width=1119,
        window_outer_height=679,
        window_inner_width=1026,
        window_inner_height=532,
        screen_width=1773,
        screen_height=1108,
        screen_avail_width=1773,
        screen_avail_height=1108,
        window_offset_x=447,
        window_offset_y=222,
        element_rect=DisplayRectangle(Point(10, 20), 30, 40))

    self.assertEqual(viewport_info.browser_viewable,
                     DisplayRectangle(Point(726, 522), 1817, 942))
    self.assertEqual(
        viewport_info.element_rect,
        DisplayRectangle(
            Point(744, 557), round(30 * 1.77125), round(40 * 1.77125)))

  def test_mobile_viewport_scaling_zoom_out(self) -> None:
    # Simulates a mobile browser where a 980 CSS px layout viewport is scaled
    # down to fit a 360 DIP window on a 1080x1920 (DPR 3.0) display.
    viewport_info = ViewportInfo(
        device_pixel_ratio=3.0,
        window_outer_width=360,
        window_outer_height=616,
        window_inner_width=980,
        window_inner_height=1402,
        screen_width=360,
        screen_height=640,
        screen_avail_width=360,
        screen_avail_height=640,
        window_offset_x=0,
        window_offset_y=0,
        element_rect=DisplayRectangle(Point(8, 8), 25, 19))

    self.assertAlmostEqual(viewport_info.actual_pixel_ratio, 1080 / 980)
    self.assertEqual(viewport_info.native_screen,
                     DisplayRectangle(Point(0, 0), 1080, 1920))
    self.assertEqual(viewport_info.browser_viewable,
                     DisplayRectangle(Point(0, 303), 1080, 1545))
    self.assertEqual(viewport_info.element_rect,
                     DisplayRectangle(Point(9, 312), 28, 21))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
