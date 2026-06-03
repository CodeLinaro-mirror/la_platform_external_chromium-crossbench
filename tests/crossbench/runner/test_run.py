# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench.probes.screenshot import ScreenshotProbe
from crossbench.runner.run import Run
from crossbench.runner.run_annotation import RunAnnotation
from tests import test_helper
from tests.crossbench.mock_helper import MockStory
from tests.crossbench.runner.groups.base import BaseRunGroupTestCase
from tests.crossbench.runner.helper import MockProbe

if TYPE_CHECKING:
  from crossbench.runner.runner import Runner

class RunTestCase(BaseRunGroupTestCase):

  @override
  def default_runner(self) -> Runner:
    return super().default_runner(create_symlinks=False)

  def _create_run(self) -> Run:
    session = self.default_session()
    return Run(self.runner, session, MockStory("mock story"), 1, False,
               "1_default", 1, "test run", dt.timedelta(minutes=1), True)

  def _run_actions_and_get_new_marks(self, **kwargs) -> list[str]:
    run = self._create_run()
    initial_marks = list(run.browser.performance_marks)
    with run.actions("Some_Custom_Action", **kwargs):
      pass
    new_marks = run.browser.performance_marks
    self.assertListEqual(new_marks[:len(initial_marks)], initial_marks)
    return new_marks[len(initial_marks):]

  def test_find_probe_context(self):
    self.runner.attach_probe(MockProbe())
    run = self._create_run()
    session = run.browser_session
    session.set_ready()
    with session.open():
      self.assertIsNotNone(run.get_probe_context(MockProbe))
      self.assertIsNone(run.get_probe_context(ScreenshotProbe))

  def test_annotate(self):
    run = self._create_run()
    self.assertFalse(list(run.annotations))
    annotation = RunAnnotation.warning("Some warning")

    with self.assertNoLogs(level="INFO"):
      run.log_annotations()

    run.annotate(annotation)
    self.assertIn(annotation, run.annotations)
    with self.assertLogs(level="INFO") as cm:
      run.log_annotations()
    self.assertIn("Some warning", " ".join(cm.output))

  def test_actions_no_performance_mark(self):
    self.assertListEqual(self._run_actions_and_get_new_marks(), [])

  def test_actions_explicit_empty_performance_mark(self):
    self.assertListEqual(
        self._run_actions_and_get_new_marks(performance_mark=""), [])

  def test_actions_with_performance_mark(self):
    self.assertListEqual(
        self._run_actions_and_get_new_marks(performance_mark="custom-marker"),
        ["crossbench-custom-marker-start", "crossbench-custom-marker-stop"])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
