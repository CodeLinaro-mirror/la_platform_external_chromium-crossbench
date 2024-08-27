# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from crossbench.benchmarks.loading.action_runner.android_input_action_runner \
  import ViewportInfo, DisplayRectangle


class ViewportInfoTestCase(unittest.TestCase):

  def test_display_rectangle_mul(self):
    rect: DisplayRectangle = DisplayRectangle(1, 2, 3, 4)

    rect = rect * 5

    self.assertEqual(rect.left, 5)
    self.assertEqual(rect.right, 10)
    self.assertEqual(rect.top, 15)
    self.assertEqual(rect.bottom, 20)

  def test_display_rectangle_add(self):
    rect: DisplayRectangle = DisplayRectangle(1, 2, 3, 4)
    rect2: DisplayRectangle = DisplayRectangle(10, 20, 30, 40)

    rect = rect + rect2

    self.assertEqual(rect.left, 11)
    self.assertEqual(rect.right, 12)
    self.assertEqual(rect.top, 33)
    self.assertEqual(rect.bottom, 34)
