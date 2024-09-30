# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from crossbench.benchmarks.loading.action_runner.display_rectangle \
    import DisplayRectangle
from crossbench.benchmarks.loading.point import Point


class DisplayRectangleTestCase(unittest.TestCase):

  def test_display_rectangle_mul(self):
    rect: DisplayRectangle = DisplayRectangle(Point(1, 2), 3, 4)

    rect = rect * 5

    self.assertEqual(rect.origin.x, 5)
    self.assertEqual(rect.origin.y, 10)
    self.assertEqual(rect.width, 15)
    self.assertEqual(rect.height, 20)

  def test_display_rectangle_shift_by(self):
    rect: DisplayRectangle = DisplayRectangle(Point(1, 2), 3, 4)
    rect2: DisplayRectangle = DisplayRectangle(Point(10, 20), 30, 40)

    rect = rect.shift_by(rect2)

    self.assertEqual(rect.origin.x, 11)
    self.assertEqual(rect.origin.y, 22)
    self.assertEqual(rect.width, 3)
    self.assertEqual(rect.height, 4)

  def test_display_rectangle_mid_x(self):
    rect: DisplayRectangle = DisplayRectangle(Point(1, 2), 6, 8)

    self.assertEqual(rect.mid_x, 4)

  def test_display_rectangle_mid_y(self):
    rect: DisplayRectangle = DisplayRectangle(Point(1, 2), 6, 8)

    self.assertEqual(rect.mid_y, 6)

  def test_display_rectangle_middle(self):
    rect: DisplayRectangle = DisplayRectangle(Point(1, 2), 6, 8)

    self.assertEqual(rect.middle, Point(4, 6))

  def test_display_rectangle_truthy(self):
    self.assertFalse(DisplayRectangle(Point(1, 2), 0, 0))
    self.assertFalse(DisplayRectangle(Point(5, 6), 0, 1))
    self.assertFalse(DisplayRectangle(Point(3, 4), 1, 0))
    self.assertTrue(DisplayRectangle(Point(1, 2), 1, 1))
