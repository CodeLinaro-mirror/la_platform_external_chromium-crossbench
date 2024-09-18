# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import pathlib
import unittest

from crossbench.browsers.browser import Browser
from crossbench.env import HostEnvironment
from crossbench.flags.base import Flags
from crossbench.helper.state import UnexpectedStateError
from crossbench.probes import all as all_probes
from crossbench.probes.probe import ProbeIncompatibleBrowser
from crossbench.runner.groups.session import BrowserSessionRunGroup
from crossbench.runner.groups.thread import RunThreadGroup
from crossbench.runner.runner import Runner, ThreadMode
from tests import test_helper
from tests.crossbench.mock_browser import MockChromeDev
from tests.crossbench.mock_helper import MockBenchmark
from tests.crossbench.runner.helper import (BaseRunnerTestCase, MockBrowser,
                                            MockPlatform, MockProbe,
                                            MockProbeContext, MockRun,
                                            MockRunner)


# Skip strict type checks for better mocking
# pytype: disable=wrong-arg-types
class TestThreadModeTestCase(unittest.TestCase):
  # pylint has some issues with enums.
  # pylint: disable=no-member

  def create_session(self, browser, index) -> BrowserSessionRunGroup:
    return BrowserSessionRunGroup(
        self.env,
        self.probes,
        browser,
        Flags(),
        index,
        self.root_dir,
        create_symlinks=True,
        throw=True)

  def setUp(self) -> None:
    self.platform_a = MockPlatform("platform a")
    self.platform_b = MockPlatform("platform b")
    self.browser_a_1 = MockBrowser("mock browser a 1", self.platform_a)
    self.browser_a_2 = MockBrowser("mock browser b 1", self.platform_a)
    self.browser_b_1 = MockBrowser("mock browser b 1", self.platform_b)
    self.browser_b_2 = MockBrowser("mock browser b 2", self.platform_b)
    self.runner = MockRunner()
    self.root_dir = pathlib.Path()
    self.env = self.runner.env
    self.probes = []
    self.runs = (
        MockRun(self.runner, self.create_session(self.browser_a_1, 1), "run 1"),
        MockRun(self.runner, self.create_session(self.browser_a_2, 2), "run 2"),
        MockRun(self.runner, self.create_session(self.browser_a_1, 3), "run 3"),
        MockRun(self.runner, self.create_session(self.browser_a_2, 4), "run 4"),
        MockRun(self.runner, self.create_session(self.browser_b_1, 5), "run 5"),
        MockRun(self.runner, self.create_session(self.browser_b_2, 6), "run 6"),
        MockRun(self.runner, self.create_session(self.browser_b_1, 7), "run 7"),
        MockRun(self.runner, self.create_session(self.browser_b_2, 8), "run 8"),
    )
    self.runner.runs = self.runs

  def test_default_runs(self):
    session_ids = {run.browser_session.index for run in self.runs}
    self.assertEqual(len(session_ids), len(self.runs))

  def test_group_none(self):
    groups = ThreadMode.NONE.group(self.runs)
    self.assertEqual(len(groups), 1)
    self.assertTupleEqual(groups[0].runs, self.runs)
    self.assertEqual(groups[0].index, 0)

  def test_group_platform(self):
    groups = ThreadMode.PLATFORM.group(self.runs)
    self.assertEqual(len(groups), 2)
    group_a, group_b = groups
    self.assertTupleEqual(group_a.runs, self.runs[:4])
    self.assertTupleEqual(group_b.runs, self.runs[4:])
    self.assertEqual(group_a.index, 0)
    self.assertEqual(group_b.index, 1)

  def test_group_browser(self):
    groups = ThreadMode.BROWSER.group(self.runs)
    self.assertEqual(len(groups), 4)
    self.assertTupleEqual(groups[0].runs, (self.runs[0], self.runs[2]))
    self.assertTupleEqual(groups[1].runs, (self.runs[1], self.runs[3]))
    self.assertTupleEqual(groups[2].runs, (self.runs[4], self.runs[6]))
    self.assertTupleEqual(groups[3].runs, (self.runs[5], self.runs[7]))
    for index, group in enumerate(groups):
      self.assertEqual(group.index, index)

  def test_group_session(self):
    groups = ThreadMode.SESSION.group(self.runs)
    self.assertEqual(len(groups), len(self.runs))
    for group, run in zip(groups, self.runs):
      self.assertTupleEqual(group.runs, (run,))
    for index, group in enumerate(groups):
      self.assertEqual(group.index, index)

  def test_group_session_2(self):
    session_1 = self.create_session(self.browser_a_1, 1)
    session_2 = self.create_session(self.browser_a_2, 2)
    runs = (
        MockRun(self.runner, session_1, "story 1"),
        MockRun(self.runner, session_2, "story 2"),
        MockRun(self.runner, session_1, "story 3"),
        MockRun(self.runner, session_2, "story 4"),
    )
    groups = ThreadMode.SESSION.group(runs)
    group_a, group_b = groups
    self.assertTupleEqual(group_a.runs, (runs[0], runs[2]))
    self.assertTupleEqual(group_b.runs, (runs[1], runs[3]))
    for index, group in enumerate(groups):
      self.assertEqual(group.index, index)


class RunnerTestCase(BaseRunnerTestCase):

  def test_default_instance(self):
    runner = self.default_runner()
    self.assertSequenceEqual(self.stories, runner.stories)
    self.assertSequenceEqual(self.browsers, runner.browsers)
    self.assertEqual(runner.repetitions, 1)
    self.assertEqual(len(runner.platforms), 1)
    self.assertTrue(runner.exceptions.is_success)
    default_probes = list(runner.default_probes)
    self.assertListEqual(list(runner.probes), default_probes)
    self.assertEqual(len(default_probes), len(all_probes.INTERNAL_PROBES))
    self.assertEqual(len(runner.runs), 0)
    # no runs => is_success == false
    self.assertFalse(runner.is_success)

  def test_dry_run(self):
    self.test_run(is_dry_run=True)

  def test_run(self, is_dry_run=False):
    runner = self.default_runner()

    runner.run(is_dry_run)
    # Don't reuse the Runner:
    with self.assertRaises(UnexpectedStateError):
      runner.run(is_dry_run)

    self.assertEqual(len(runner.runs), 4)
    self.assertTrue(runner.is_success)
    for run in runner.runs:
      self.assertTrue(run.is_success)
      self.assertEqual(len(run.results), len(all_probes.INTERNAL_PROBES))
      for probe in runner.probes:
        self.assertIn(probe, run.results)

  def test_run_mock_probe(self):
    runner = self.default_runner()
    probe = MockProbe("custom_probe_data")
    runner.attach_probe(probe)
    self.assertIn(probe, runner.probes)
    for browser in runner.browsers:
      self.assertIn(probe, browser.probes)

    runner.run()
    self.assertTrue(runner.is_success)
    for run in runner.runs:
      results = run.results[probe]
      with results.json.open() as f:
        probe_data = json.load(f)
        self.assertEqual(probe_data, "custom_probe_data")

  def test_attach_probe_twice(self):
    runner = self.default_runner()
    probe = MockProbe("custom_probe_data")
    runner.attach_probe(probe)
    # Cannot attach same probe twice.
    with self.assertRaises(ValueError) as cm:
      runner.attach_probe(probe)
    self.assertIn("twice", str(cm.exception))
    self.assertIn(probe, runner.probes)
    self.assertNotIn(probe, runner.default_probes)

  def test_attach_incompatible_probe(self):
    runner = self.default_runner()
    probe = MockProbe("custom_probe_data")

    def mock_validate_browser(env: HostEnvironment, browser: Browser):
      del env
      nonlocal probe
      raise ProbeIncompatibleBrowser(probe, browser, "mock invalid")

    probe.validate_browser = mock_validate_browser
    with self.assertRaises(ProbeIncompatibleBrowser) as cm:
      runner.attach_probe(probe)
    self.assertIn("mock invalid", str(cm.exception))
    # matching_browser_only = True silence the error
    runner.attach_probe(probe, matching_browser_only=True)
    # No browser matches => probe is not available
    self.assertNotIn(probe, runner.probes)
    self.assertNotIn(probe, runner.default_probes)
    for browser in self.browsers:
      self.assertNotIn(probe, browser.probes)

  def test_attach_partially_incompatible_probe(self):
    runner = self.default_runner()
    probe = MockProbe("custom_probe_data")
    compatible_browser = self.browsers[1]

    def mock_validate_browser(env: HostEnvironment, browser: Browser):
      del env
      nonlocal probe
      nonlocal compatible_browser
      if browser != compatible_browser:
        raise ProbeIncompatibleBrowser(probe, browser, "mock invalid")

    # Attaching incompatible probes raises errors by default.
    probe.validate_browser = mock_validate_browser
    with self.assertRaises(ProbeIncompatibleBrowser) as cm:
      runner.attach_probe(probe)
    self.assertIn("mock invalid", str(cm.exception))
    # matching_browser_only = True silences the error
    runner.attach_probe(probe, matching_browser_only=True)
    self.assertIn(probe, runner.probes)
    self.assertNotIn(probe, runner.default_probes)
    for browser in self.browsers:
      if browser == compatible_browser:
        self.assertIn(probe, browser.probes)
      else:
        self.assertNotIn(probe, browser.probes)


class CustomException(Exception):
  pass


def run_setup_fail(is_dry_run):
  raise CustomException()


class RunThreadGroupTestCase(BaseRunnerTestCase):

  def tearDown(self) -> None:
    for browser in self.browsers:
      self.assertFalse(browser.is_running)
    return super().tearDown()

  def test_create_no_runs(self):
    with self.assertRaises(AssertionError):
      RunThreadGroup([])

  def test_different_runners(self):
    runs_a = list(self.default_runner().get_runs())
    self.out_dir = self.out_dir.parent / "second_out_dir"
    runner_b = Runner(
        self.out_dir, [MockChromeDev("chrome-dev-2")],
        self.benchmark,
        platform=self.platform,
        throw=True)
    runs_b = list(runner_b.get_runs())
    self.assertNotEqual(runs_a[0].runner, runs_b[0].runner)
    with self.assertRaises(AssertionError) as cm:
      RunThreadGroup(runs_a + runs_b)
    self.assertIn("same Runner", str(cm.exception))

  def test_simple_runs(self):
    runner = self.default_runner()
    runs = tuple(runner.get_runs())
    thread = RunThreadGroup(runs)
    self.assertEqual(thread.index, 0)
    self.assertEqual(thread.runner, runner)
    self.assertSequenceEqual(thread.runs, runs)
    self.assertTrue(thread.is_success)

    run_count = 0

    def test_run(run_method):
      nonlocal run_count
      run_count += 1
      run_method(is_dry_run=False)

    for run in runs:
      run.run = (lambda run_method: lambda is_dry_run: test_run(run_method))(
          run.run)

    thread.run()

    self.assertTrue(thread.is_success)
    self.assertSequenceEqual(thread.runs, runs)
    self.assertEqual(run_count, 4)

  def test_run_fail_run_probe_get_context(self):
    # 2 runs, same browser different stories
    runner = self.default_runner(browsers=[self.browsers[1]], throw=False)
    probe = MockProbe("custom_probe_data")
    runner.attach_probe(probe)
    self.assertTrue(probe.is_attached)
    runs = tuple(runner.get_runs())
    thread = RunThreadGroup(runs)
    failing_session, successful_session = thread.browser_sessions
    failing_run, successful_run = runs

    setup_fail_count = 0

    def mock_get_context_fail(run):
      if run == successful_run:
        return MockProbeContext(probe, run)
      nonlocal setup_fail_count
      setup_fail_count += 1
      raise CustomException()

    probe.get_context = mock_get_context_fail

    self.assertEqual(setup_fail_count, 0)
    thread.run()
    self.assertEqual(setup_fail_count, 1)

    self.assertTrue(successful_session.is_success)
    self.assertTrue(successful_run.is_success)

    # Errors are propagated up:
    for exceptions_holder in (runner, thread, failing_session, failing_run):
      self.assertFalse(exceptions_holder.is_success)
      exceptions = exceptions_holder.exceptions
      self.assertEqual(len(exceptions), 1)
      exception_entry = exceptions[0]
      self.assertIsInstance(exception_entry.exception, CustomException)

  def test_run_fail_run_probe_setup(self):
    # 2 runs, same browser different stories
    runner = self.default_runner(browsers=[self.browsers[1]], throw=False)
    probe = MockProbe("custom_probe_data")
    runner.attach_probe(probe)
    self.assertTrue(probe.is_attached)
    runs = tuple(runner.get_runs())
    thread = RunThreadGroup(runs)
    failing_session, successful_session = thread.browser_sessions
    failing_run, successful_run = runs

    setup_fail_count = 0

    def mock_setup_fail() -> None:
      nonlocal setup_fail_count
      setup_fail_count += 1
      raise CustomException()

    def mock_get_context_fail(run):
      context = MockProbeContext(probe, run)
      if run == failing_run:
        context.setup = mock_setup_fail
      return context

    probe.get_context = mock_get_context_fail

    self.assertEqual(setup_fail_count, 0)
    thread.run()
    self.assertEqual(setup_fail_count, 1)

    self.assertTrue(successful_session.is_success)
    self.assertTrue(successful_run.is_success)

    # Errors are propagated up:
    for exceptions_holder in (runner, thread, failing_session, failing_run):
      self.assertFalse(exceptions_holder.is_success)
      exceptions = exceptions_holder.exceptions
      self.assertEqual(len(exceptions), 1)
      exception_entry = exceptions[0]
      self.assertIsInstance(exception_entry.exception, CustomException)

  def test_run_fail_one_browser_setup(self):
    # 2 runs, same story, different browsers
    benchmark = MockBenchmark(stories=[self.stories[0]])
    runner = Runner(
        self.out_dir, self.browsers, benchmark, platform=self.platform)
    runs = tuple(runner.get_runs())
    thread = RunThreadGroup(runs)
    failing_session, successful_session = thread.browser_sessions
    failing_run, successful_run = runs
    self.assertNotEqual(failing_run.browser, successful_run.browser)

    setup_fail_count = 0

    def mock_start_fail(session: BrowserSessionRunGroup) -> None:
      del session
      nonlocal setup_fail_count
      setup_fail_count += 1
      raise CustomException()

    failing_run.browser.start = mock_start_fail

    self.assertEqual(setup_fail_count, 0)
    thread.run()
    self.assertEqual(setup_fail_count, 1)

    self.assertTrue(successful_session.is_success)
    self.assertTrue(successful_run.is_success)

    # browser startup failures should also propagate down to all runs.
    for exceptions_holder in (runner, thread, failing_session, failing_run):
      self.assertFalse(exceptions_holder.is_success)
      exceptions = exceptions_holder.exceptions
      self.assertEqual(len(exceptions), 1)
      exception_entry = exceptions[0]
      self.assertIsInstance(exception_entry.exception, CustomException)

  def test_run_fail_run(self):
    # 4 runs = (2 browser) x (2 stories)
    runner = self.default_runner(throw=False)
    runs = tuple(runner.get_runs())
    thread = RunThreadGroup(runs)
    failing_run = runs[0]
    failing_session = failing_run.browser_session

    run_fail_count = 0

    def mock_run_story_fail():
      nonlocal run_fail_count
      run_fail_count += 1
      raise CustomException()

    failing_run._run_story = mock_run_story_fail

    self.assertEqual(run_fail_count, 0)
    thread.run()
    self.assertEqual(run_fail_count, 1)

    for session in thread.browser_sessions:
      if session != failing_run.browser_session:
        self.assertTrue(session.is_success)
    for run in runs:
      if run != failing_run:
        self.assertTrue(run.is_success)

    # Errors are propagate up:
    for exceptions_holder in (runner, thread, failing_session, failing_run):
      self.assertFalse(exceptions_holder.is_success)
      exceptions = exceptions_holder.exceptions
      self.assertEqual(len(exceptions), 1)
      exception_entry = exceptions[0]
      self.assertIsInstance(exception_entry.exception, CustomException)

# pytype: enable=wrong-arg-types

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
