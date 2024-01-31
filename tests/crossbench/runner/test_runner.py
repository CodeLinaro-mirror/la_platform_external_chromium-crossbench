# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import pathlib
import unittest
from crossbench.runner.groups import BrowserSessionRunGroup
from crossbench.runner.runner import ThreadMode

from crossbench.runner.timing import SAFE_MAX_TIMEOUT_TIMEDELTA, Timing

import datetime as dt

from tests import test_helper


class TimingTestCase(unittest.TestCase):

  def test_default_instance(self):
    t = Timing()
    self.assertEqual(t.unit, dt.timedelta(seconds=1))
    self.assertEqual(t.timeout_unit, dt.timedelta())
    self.assertEqual(t.timedelta(10), dt.timedelta(seconds=10))
    self.assertEqual(t.units(1), 1)
    self.assertEqual(t.units(dt.timedelta(seconds=1)), 1)

  def test_default_instance_slowdown(self):
    t = Timing(
        unit=dt.timedelta(seconds=10), timeout_unit=dt.timedelta(seconds=11))
    self.assertEqual(t.unit, dt.timedelta(seconds=10))
    self.assertEqual(t.timeout_unit, dt.timedelta(seconds=11))
    self.assertEqual(t.timedelta(10), dt.timedelta(seconds=100))
    self.assertEqual(t.units(100), 10)
    self.assertEqual(t.units(dt.timedelta(seconds=100)), 10)
    self.assertEqual(t.timeout_timedelta(10), dt.timedelta(seconds=110))

  def test_default_instance_speedup(self):
    t = Timing(unit=dt.timedelta(seconds=0.1))
    self.assertEqual(t.unit, dt.timedelta(seconds=0.1))
    self.assertEqual(t.timedelta(10), dt.timedelta(seconds=1))
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

  def test_timeout_timing(self):
    t = Timing(
        unit=dt.timedelta(seconds=1), timeout_unit=dt.timedelta(seconds=10))
    self.assertEqual(t.timedelta(12).total_seconds(), 12)
    self.assertEqual(t.timeout_timedelta(12).total_seconds(), 120)

  def test_timeout_timing_invalid(self):
    with self.assertRaises(ValueError):
      _ = Timing(
          unit=dt.timedelta(seconds=1), timeout_unit=dt.timedelta(seconds=0.1))
    with self.assertRaises(ValueError):
      _ = Timing(
          unit=dt.timedelta(seconds=1), timeout_unit=dt.timedelta(seconds=-1))

  def test_no_timeout(self):
    self.assertFalse(Timing().has_no_timeout)
    t = Timing(timeout_unit=dt.timedelta.max)
    self.assertTrue(t.has_no_timeout)
    self.assertEqual(t.timedelta(12).total_seconds(), 12)
    self.assertEqual(t.timeout_timedelta(0.000001), SAFE_MAX_TIMEOUT_TIMEDELTA)
    self.assertEqual(t.timeout_timedelta(12), SAFE_MAX_TIMEOUT_TIMEDELTA)

  def test_timeout_overflow(self):
    t = Timing(timeout_unit=dt.timedelta(days=1000))
    self.assertEqual(t.timeout_timedelta(12), SAFE_MAX_TIMEOUT_TIMEDELTA)
    self.assertEqual(t.timeout_timedelta(1500), SAFE_MAX_TIMEOUT_TIMEDELTA)


class MockBrowser:

  def __init__(self, unique_name: str, platform) -> None:
    self.unique_name = unique_name
    self.platform = platform
    self.network = MockNetwork()

  def __str__(self):
    return self.unique_name


class MockRun:

  def __init__(self, runner, browser_session, name) -> None:
    self.runner = runner
    self.browser_session = browser_session
    self.browser = browser_session.browser
    self.platform = self.browser.platform
    self.name = name

  def __str__(self):
    return self.name


class MockPlatform:

  def __init__(self, name) -> None:
    self.name = name

  def __str__(self):
    return self.name


class MockRunner:

  def __init__(self) -> None:
    self.runs = tuple()


class MockNetwork:
  pass

# Skip strict type checks for better mocking
# pytype: disable=wrong-arg-types
class TestThreadModeTestCase(unittest.TestCase):
  # pylint has some issues with enums.
  # pylint: disable=no-member

  def setUp(self) -> None:
    self.platform_a = MockPlatform("platform a")
    self.platform_b = MockPlatform("platform b")
    self.browser_a_1 = MockBrowser("mock browser a 1", self.platform_a)
    self.browser_a_2 = MockBrowser("mock browser b 1", self.platform_a)
    self.browser_b_1 = MockBrowser("mock browser b 1", self.platform_b)
    self.browser_b_2 = MockBrowser("mock browser b 2", self.platform_b)
    self.runner = MockRunner()
    self.root_dir = pathlib.Path()
    self.runs = (
        MockRun(
            self.runner,
            BrowserSessionRunGroup(
                self.runner, self.browser_a_1, 1, self.root_dir, throw=True),
            "run 1"),
        MockRun(
            self.runner,
            BrowserSessionRunGroup(
                self.runner, self.browser_a_2, 2, self.root_dir, throw=True),
            "run 2"),
        MockRun(
            self.runner,
            BrowserSessionRunGroup(
                self.runner, self.browser_a_1, 3, self.root_dir, throw=True),
            "run 3"),
        MockRun(
            self.runner,
            BrowserSessionRunGroup(
                self.runner, self.browser_a_2, 4, self.root_dir, throw=True),
            "run 4"),
        MockRun(
            self.runner,
            BrowserSessionRunGroup(
                self.runner, self.browser_b_1, 5, self.root_dir, throw=True),
            "run 5"),
        MockRun(
            self.runner,
            BrowserSessionRunGroup(
                self.runner, self.browser_b_2, 6, self.root_dir, throw=True),
            "run 6"),
        MockRun(
            self.runner,
            BrowserSessionRunGroup(
                self.runner, self.browser_b_1, 7, self.root_dir, throw=True),
            "run 7"),
        MockRun(
            self.runner,
            BrowserSessionRunGroup(
                self.runner, self.browser_b_2, 8, self.root_dir, throw=True),
            "run 8"),
    )
    self.runner.runs = self.runs

  def test_group_none(self):
    groups = ThreadMode.NONE.group(self.runs)
    self.assertEqual(len(groups), 1)
    self.assertTupleEqual(groups[0].runs, self.runs)

  def test_group_platform(self):
    groups = ThreadMode.PLATFORM.group(self.runs)
    self.assertEqual(len(groups), 2)
    group_a, group_b = groups
    self.assertTupleEqual(group_a.runs, self.runs[:4])
    self.assertTupleEqual(group_b.runs, self.runs[4:])

  def test_group_browser(self):
    groups = ThreadMode.BROWSER.group(self.runs)
    self.assertEqual(len(groups), 4)
    self.assertTupleEqual(groups[0].runs, (self.runs[0], self.runs[2]))
    self.assertTupleEqual(groups[1].runs, (self.runs[1], self.runs[3]))
    self.assertTupleEqual(groups[2].runs, (self.runs[4], self.runs[6]))
    self.assertTupleEqual(groups[3].runs, (self.runs[5], self.runs[7]))

  def test_group_session(self):
    groups = ThreadMode.SESSION.group(self.runs)
    self.assertEqual(len(groups), len(self.runs))
    for group, run in zip(groups, self.runs):
      self.assertTupleEqual(group.runs, (run,))

  def test_group_session_2(self):
    session_1 = BrowserSessionRunGroup(self.runner, self.browser_a_1, 1,
                                       self.root_dir, True)
    session_2 = BrowserSessionRunGroup(self.runner, self.browser_a_2, 2,
                                       self.root_dir, True)
    runs = (
        MockRun(self.runner, session_1, "run 1"),
        MockRun(self.runner, session_2, "run 2"),
        MockRun(self.runner, session_1, "run 3"),
        MockRun(self.runner, session_2, "run 4"),
    )
    groups = ThreadMode.SESSION.group(runs)
    group_a, group_b = groups
    self.assertTupleEqual(group_a.runs, (runs[0], runs[2]))
    self.assertTupleEqual(group_b.runs, (runs[1], runs[3]))


# pytype: enable=wrong-arg-types

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
