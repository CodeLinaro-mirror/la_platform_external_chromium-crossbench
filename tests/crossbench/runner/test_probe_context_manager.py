# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

from typing_extensions import override

from crossbench.helper.state import UnexpectedStateError
from crossbench.runner.groups.session import ProbeSessionContextManager
from crossbench.runner.run import ProbeRunContextManager

if TYPE_CHECKING:
  from crossbench.probes.probe_context import ProbeSessionContext

from tests import test_helper
from tests.crossbench.runner.helper import BaseRunnerTestCase, MockProbe, \
    MockProbeContext
from tests.crossbench.test_exception import CustomException


class FailingMockProbeContext(MockProbeContext):

  @override
  def setup(self):
    raise CustomException("failing setup")


class MockSessionProbe(MockProbe):

  @override
  def create_session_context(self, session) -> ProbeSessionContext | None:
    mock_context = mock.MagicMock()
    mock_context.name = "mock_session_context"
    return mock_context


class ProbeContextManagerTestCase(BaseRunnerTestCase):

  def setup_context_manager(self, throw: bool = True):
    self.runner = self.single_story_runner(throw=throw)
    self.cb_run = next(iter(self.runner._get_runs()))
    self.context_manager = ProbeRunContextManager(self.cb_run,
                                                  self.cb_run.results)

  def test_basic_accessor(self):
    self.setup_context_manager()
    self.assertTrue(self.context_manager.is_success)
    self.assertFalse(self.context_manager.is_ready)
    self.assertFalse(self.context_manager.is_running)

  def test_wrong_order(self):
    self.setup_context_manager()
    with self.assertRaisesRegex(UnexpectedStateError, "INITIAL"):
      with self.context_manager.open(is_dry_run=False):
        pass
    with self.assertRaisesRegex(UnexpectedStateError, "INITIAL"):
      self.context_manager.teardown(is_dry_run=False)

  def test_setup_no_probes(self):
    self.setup_context_manager()
    self.assertFalse(self.context_manager.is_ready)
    with self.assertRaises(AssertionError):
      self.context_manager.setup([], is_dry_run=False)
    self.assertFalse(self.context_manager.is_ready)

  def test_setup_detached_probe(self):
    self.setup_context_manager()
    probe = MockProbe("custom_probe_data")
    self.assertFalse(self.context_manager.is_ready)
    with self.assertRaisesRegex(AssertionError, "attached"):
      self.context_manager.setup([probe], is_dry_run=False)
    self.assertFalse(self.context_manager.is_ready)

  def test_setup_single_probe(self):
    self.setup_context_manager()
    probe = MockProbe("custom_probe_data")
    self.runner.attach_probe(probe)
    self.assertFalse(self.context_manager.is_ready)
    self.context_manager.setup([probe], is_dry_run=False)
    self.assertTrue(self.context_manager.is_ready)

  def test_setup_single_probe_dry_run(self):
    self.setup_context_manager()
    probe = MockProbe("custom_probe_data")
    self.runner.attach_probe(probe)
    self.assertFalse(self.context_manager.is_ready)
    self.context_manager.setup([probe], is_dry_run=True)
    self.assertFalse(self.context_manager.is_running)
    self.assertTrue(self.context_manager.is_ready)

  def test_setup_teardown_dry_run(self):
    self.setup_context_manager()
    probe = MockProbe("custom_probe_data")
    self.runner.attach_probe(probe)
    self.context_manager.setup([probe], is_dry_run=True)
    self.assertTrue(self.context_manager.is_ready)
    self.context_manager.teardown(is_dry_run=True)
    self.assertFalse(self.context_manager.is_ready)
    self.assertNotIn(probe, self.cb_run.results)

  def test_direct_setup_teardown(self):
    self.setup_context_manager()
    probe = MockProbe("custom_probe_data")
    self.runner.attach_probe(probe)
    self.cb_run.out_dir.mkdir(parents=True)
    self.context_manager.setup([probe], is_dry_run=False)
    self.assertTrue(self.context_manager.is_ready)
    self.context_manager.teardown(is_dry_run=False)
    self.assertFalse(self.context_manager.is_ready)
    self.assertTrue(self.context_manager.is_success)
    children = list(self.cb_run.out_dir.iterdir())
    self.assertEqual(len(children), 1)
    result_file = self.cb_run.results[probe].file
    self.assertTrue(result_file.exists())
    self.assertEqual(result_file, children[0])

  def test_setup_open_teardown_dry_run(self):
    self.setup_context_manager()
    probe = MockProbe("custom_probe_data")
    self.runner.attach_probe(probe)
    self.context_manager.setup([probe], is_dry_run=True)
    self.assertFalse(self.context_manager.is_running)
    with self.context_manager.open(is_dry_run=True):
      self.assertTrue(self.context_manager.is_running)
    self.context_manager.teardown(is_dry_run=True)
    self.assertFalse(self.context_manager.is_running)
    self.assertTrue(self.context_manager.is_success)
    self.assertNotIn(probe, self.cb_run.results)

  def test_setup_open_teardown(self):
    self.setup_context_manager()
    probe = MockProbe("custom_probe_data")
    self.runner.attach_probe(probe)
    self.cb_run.out_dir.mkdir(parents=True)
    self.context_manager.setup([probe], is_dry_run=False)
    self.assertFalse(self.context_manager.is_running)
    with self.context_manager.open(is_dry_run=False):
      self.assertTrue(self.context_manager.is_running)
    self.context_manager.teardown(is_dry_run=False)
    self.assertFalse(self.context_manager.is_running)
    self.assertTrue(self.context_manager.is_success)
    children = list(self.cb_run.out_dir.iterdir())
    self.assertEqual(len(children), 1)
    result_file = self.cb_run.results[probe].file
    self.assertTrue(result_file.exists())
    self.assertEqual(result_file, children[0])

  def test_setup_error_throw(self):
    self.setup_context_manager()
    probe = MockProbe("custom_probe_data", FailingMockProbeContext)
    self.runner.attach_probe(probe)
    with self.assertRaisesRegex(CustomException, "failing setup"):
      self.context_manager.setup([probe], is_dry_run=False)
    self.assertFalse(self.context_manager.is_success)

  def test_setup_error(self):
    self.setup_context_manager(throw=False)
    probe = MockProbe("custom_probe_data", FailingMockProbeContext)
    self.runner.attach_probe(probe)

    self.context_manager.setup([probe], is_dry_run=False)
    self.assertFalse(self.context_manager.is_success)
    self.assertEqual(len(self.cb_run.exceptions), 1)
    self.assertTrue(self.cb_run.results[probe].is_empty)

    exception = self.cb_run.exceptions[0].exception
    self.assertIsInstance(exception, CustomException)


class ProbeContextManagerSelectiveAttachmentTestCase(BaseRunnerTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.runner = self.default_runner()
    self.runs = list(self.runner._get_runs())
    for run in self.runs:
      run.out_dir.mkdir(parents=True, exist_ok=True)
    self.chrome_runs = [
        run for run in self.runs if run.browser is self.mock_chrome_dev
    ]
    self.firefox_runs = [
        run for run in self.runs if run.browser is self.mock_firefox
    ]

    self.chrome_session = self.chrome_runs[0].browser_session
    self.chrome_session.path.mkdir(parents=True, exist_ok=True)
    self.firefox_session = self.firefox_runs[0].browser_session
    self.firefox_session.path.mkdir(parents=True, exist_ok=True)

  def _get_probe_contexts_after_setup(self, context_manager, probe):
    context_manager.setup([probe], is_dry_run=False)
    self.assertTrue(context_manager.is_ready)
    return context_manager._probe_contexts

  def test_run_context_manager_selective_attachment(self):
    probe = MockProbe("custom_probe_data")
    # Probe is only attached to Chrome, not Firefox.
    probe.attach(self.mock_chrome_dev)

    # Verify context creation on the attached browser.
    for run in self.chrome_runs:
      manager = ProbeRunContextManager(run, run.results)
      contexts = self._get_probe_contexts_after_setup(manager, probe)
      self.assertEqual(len(contexts), 1)
      self.assertIn(type(probe), contexts)

    # Verify context is skipped on the unattached browser.
    for run in self.firefox_runs:
      manager = ProbeRunContextManager(run, run.results)
      contexts = self._get_probe_contexts_after_setup(manager, probe)
      self.assertEqual(len(contexts), 0)

  def test_session_context_manager_selective_attachment(self):
    probe = MockSessionProbe("custom_session_probe_data")
    # Probe is only attached to Chrome, not Firefox.
    probe.attach(self.mock_chrome_dev)

    # Verify context creation on the attached browser session.
    manager_chrome = ProbeSessionContextManager(self.chrome_session,
                                                self.chrome_session.results)
    contexts_chrome = self._get_probe_contexts_after_setup(
        manager_chrome, probe)
    self.assertEqual(len(contexts_chrome), 1)
    self.assertIn(type(probe), contexts_chrome)

    # Verify context is skipped on the unattached browser session.
    manager_firefox = ProbeSessionContextManager(self.firefox_session,
                                                 self.firefox_session.results)
    contexts_firefox = self._get_probe_contexts_after_setup(
        manager_firefox, probe)
    self.assertEqual(len(contexts_firefox), 0)


del BaseRunnerTestCase

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
