# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from crossbench.runner import Timing

import datetime as dt

from tests import test_helper


class TimingTestCase(unittest.TestCase):

  def test_default_instance(self):
    t = Timing()
    self.assertEqual(t.unit, dt.timedelta(seconds=1))
    self.assertEqual(t.timedelta(10), dt.timedelta(seconds=10))
    self.assertEqual(t.timedelta(10, absolute=True), dt.timedelta(seconds=10))
    self.assertEqual(t.units(1), 1)
    self.assertEqual(t.units(dt.timedelta(seconds=1)), 1)

  def test_default_instance_slowdown(self):
    t = Timing(unit=dt.timedelta(seconds=10))
    self.assertEqual(t.unit, dt.timedelta(seconds=10))
    self.assertEqual(t.timedelta(10), dt.timedelta(seconds=100))
    self.assertEqual(t.timedelta(10, absolute=True), dt.timedelta(seconds=10))
    self.assertEqual(t.units(100), 10)
    self.assertEqual(t.units(dt.timedelta(seconds=100)), 10)

  def test_default_instance_speedup(self):
    t = Timing(unit=dt.timedelta(seconds=0.1))
    self.assertEqual(t.unit, dt.timedelta(seconds=0.1))
    self.assertEqual(t.timedelta(10), dt.timedelta(seconds=1))
    self.assertEqual(t.timedelta(10, absolute=True), dt.timedelta(seconds=10))
    self.assertEqual(t.units(1), 10)
    self.assertEqual(t.units(dt.timedelta(seconds=1)), 10)

  def test_invalid_params(self):
    with self.assertRaises(ValueError) as cm:
      _ = Timing(cool_down_time=dt.timedelta(seconds=-1))
    self.assertIn("Timing.cool_down_time", str(cm.exception))

    with self.assertRaises(ValueError) as cm:
      _ = Timing(unit=dt.timedelta(seconds=-1))
    self.assertIn("Timing.unit", str(cm.exception))
    with self.assertRaises(ValueError) as cm:
      _ = Timing(unit=dt.timedelta())
    self.assertIn("Timing.unit", str(cm.exception))

    with self.assertRaises(ValueError) as cm:
      _ = Timing(run_timeout=dt.timedelta(seconds=-1))
    self.assertIn("Timing.run_timeout", str(cm.exception))

  def test_to_units(self):
    t = Timing()
    self.assertEqual(t.units(100), 100)
    self.assertEqual(t.units(dt.timedelta(minutes=1.5)), 90)
    with self.assertRaises(ValueError):
      _ = t.timedelta(-1)

    t = Timing(unit=dt.timedelta(seconds=10))
    self.assertEqual(t.units(100), 10)
    self.assertEqual(t.units(dt.timedelta(minutes=1.5)), 9)
    with self.assertRaises(ValueError):
      _ = t.timedelta(-1)

    t = Timing(unit=dt.timedelta(seconds=0.1))
    self.assertEqual(t.units(100), 1000)
    self.assertEqual(t.units(dt.timedelta(minutes=1.5)), 900)
    with self.assertRaises(ValueError):
      _ = t.timedelta(-1)

  def test_to_timedelta(self):
    t = Timing()
    self.assertEqual(t.timedelta(12).total_seconds(), 12)
    self.assertEqual(t.timedelta(dt.timedelta(minutes=1.5)).total_seconds(), 90)
    with self.assertRaises(ValueError):
      _ = t.timedelta(-1)

    t = Timing(unit=dt.timedelta(seconds=10))
    self.assertEqual(t.timedelta(12).total_seconds(), 120)
    self.assertEqual(
        t.timedelta(dt.timedelta(minutes=1.5)).total_seconds(), 900)
    with self.assertRaises(ValueError):
      _ = t.timedelta(-1)

    t = Timing(unit=dt.timedelta(seconds=0.5))
    self.assertEqual(t.timedelta(12).total_seconds(), 6)
    self.assertEqual(t.timedelta(dt.timedelta(minutes=1.5)).total_seconds(), 45)
    with self.assertRaises(ValueError):
      _ = t.timedelta(-1)

  def test_to_timedelta_absolute(self):
    t = Timing()
    self.assertEqual(t.timedelta(12, absolute=True).total_seconds(), 12)
    self.assertEqual(
        t.timedelta(dt.timedelta(minutes=1.5), absolute=True).total_seconds(),
        90)

    t = Timing(unit=dt.timedelta(seconds=10))
    self.assertEqual(t.timedelta(12, absolute=True).total_seconds(), 12)
    self.assertEqual(
        t.timedelta(dt.timedelta(minutes=1.5), absolute=True).total_seconds(),
        90)

    t = Timing(unit=dt.timedelta(seconds=0.5))
    self.assertEqual(t.timedelta(12, absolute=True).total_seconds(), 12)
    self.assertEqual(
        t.timedelta(dt.timedelta(minutes=1.5), absolute=True).total_seconds(),
        90)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
