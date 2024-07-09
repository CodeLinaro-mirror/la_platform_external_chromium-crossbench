# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from typing import Optional

from crossbench.browsers.browser import Browser
from crossbench.runner.groups.session import BrowserSessionRunGroup
from tests import test_helper
from tests.crossbench.runner.helper import (BaseRunnerTestCase, MockProbe,
                                            MockRun)


class BrowserSessionRunGroupTestCase(BaseRunnerTestCase):

  def setUp(self):
    super().setUp()
    self.root_dir = self.out_dir / "custom"
    self.runner = self.default_runner()

  def default_session(self, browser: Optional[Browser] = None):
    browser = browser or self.browsers[0]
    return BrowserSessionRunGroup(self.runner, browser, 0, self.root_dir, True)

  def test_basic_properties(self):
    session = self.default_session()
    self.assertIs(session.runner, self.runner)
    self.assertEqual(session.index, 0)
    self.assertIs(session.browser, self.browsers[0])
    self.assertFalse(session.is_single_run)
    self.assertFalse(session.is_running)
    self.assertEqual(session.root_dir, self.root_dir)
    self.assertFalse(session.extra_flags)
    self.assertFalse(session.extra_js_flags)
    self.assertIn("0", str(session.info_stack))
    self.assertIn(str(self.browsers[0].unique_name), str(session.info_stack))
    self.assertEqual(session.info["runs"], 0)
    self.assertEqual(session.info["index"], 0)
    self.assertIn("0", str(session))
    self.assertIn(str(self.browsers[0]), str(session))
    self.assertTrue(session.browser_tmp_dir.is_dir())
    with self.assertRaises(IndexError):
      _ = session.timing

  def test_out_dir_single_run(self):
    session = self.default_session()
    with self.assertRaises(AssertionError):
      _ = session.out_dir
    run_1 = MockRun(self.runner, session, "run 1")
    session.append(run_1)
    with self.assertRaises(AssertionError):
      _ = session.out_dir
    session.set_ready()
    self.assertEqual(session.out_dir, run_1.out_dir)
    self.assertNotEqual(session.out_dir, session.raw_session_dir)

  def test_out_dir_mulitple_runs(self):
    session = self.default_session()
    run_1 = MockRun(self.runner, session, "run 1")
    run_2 = MockRun(self.runner, session, "run 2")
    session.append(run_1)
    session.append(run_2)
    session.set_ready()
    self.assertNotEqual(session.out_dir, run_1.out_dir)
    self.assertEqual(session.out_dir, session.raw_session_dir)

  def test_append(self):
    session = self.default_session()
    run_1 = MockRun(self.runner, session, "run 1")
    session.append(run_1)
    self.assertListEqual(list(session.runs), [run_1])
    self.assertEqual(session.info["runs"], 1)
    self.assertTrue(session.is_single_run)
    self.assertFalse(session.is_running)
    self.assertIs(session.first_run, run_1)
    self.assertIs(session.timing, run_1.timing)

    run_2 = MockRun(self.runner, session, "run 2")
    session.append(run_2)
    self.assertListEqual(list(session.runs), [run_1, run_2])
    self.assertEqual(session.info["runs"], 2)

    session.set_ready()
    self.assertFalse(session.is_single_run)
    self.assertFalse(session.is_running)
    self.assertIs(session.first_run, run_1)
    self.assertFalse(session.extra_flags)
    self.assertFalse(session.extra_js_flags)

    self.assertTrue(session.is_first_run(run_1))
    self.assertFalse(session.is_first_run(run_2))

  def test_append_after_ready(self):
    session = self.default_session()
    run_1 = MockRun(self.runner, session, "run 1")
    session.append(run_1)
    session.set_ready()
    with self.assertRaises(AssertionError):
      session.append(MockRun(self.runner, session, "run 3"))

  def test_append_wrong_session(self):
    session_1 = self.default_session()
    run_1 = MockRun(self.runner, session_1, "run 0")
    session_1.append(run_1)
    session_2 = self.default_session(self.browsers[1])
    run_2 = MockRun(self.runner, session_2, "run 0")
    with self.assertRaises(AssertionError):
      session_1.append(run_2)
    run_3 = MockRun(self.runner, session_1, "run 0")
    run_3.browser = self.browsers[1]
    with self.assertRaises(AssertionError):
      session_1.append(run_3)

  def test_append_different_probes(self):
    session = self.default_session()
    run_1 = MockRun(self.runner, session, "run 0")
    run_1.probes = []
    run_2 = MockRun(self.runner, session, "run 0")
    run_2.probes = [MockProbe()]
    session.append(run_1)
    session.append(run_2)
    with self.assertRaises(ValueError):
      session.set_ready()

  def test_set_ready(self):
    with self.assertRaises(ValueError):
      session = self.default_session()
      session.set_ready()
    session = self.default_session()
    session.append(MockRun(self.runner, session, "run 0"))
    session.set_ready()
    self.assertFalse(session.extra_flags)
    self.assertFalse(session.extra_js_flags)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
