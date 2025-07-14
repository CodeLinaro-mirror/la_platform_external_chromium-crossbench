# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt

from crossbench.probes.screenshot import ScreenshotProbe
from crossbench.runner.run import Run
from crossbench.runner.run_annotation import RunAnnotation
from tests import test_helper
from tests.crossbench.mock_helper import MockStory
from tests.crossbench.runner.groups.base import BaseRunGroupTestCase
from tests.crossbench.runner.helper import MockProbe


class RunTestCase(BaseRunGroupTestCase):

  def test_find_probe_context(self):
    self.runner.attach_probe(MockProbe())
    session = self.default_session()
    run = Run(self.runner, session, MockStory("mock story"), None, 1, False,
              "1_default", 1, "test run", dt.timedelta(minutes=1), True)
    session.set_ready()
    with session.open():
      self.assertIsNotNone(run.find_probe_context(MockProbe))
      self.assertIsNone(run.find_probe_context(ScreenshotProbe))

  def test_annotate(self):
    session = self.default_session()
    run = Run(self.runner, session, MockStory("mock story"), None, 1, False,
              "1_default", 1, "test run", dt.timedelta(minutes=1), True)
    self.assertFalse(list(run.annotations))
    annotation = RunAnnotation.warning("Some warning")

    with self.assertNoLogs(level="INFO"):
      run.log_annotations()

    run.annotate(annotation)
    self.assertIn(annotation, run.annotations)
    with self.assertLogs(level="INFO") as cm:
      run.log_annotations()
    self.assertIn("Some warning", " ".join(cm.output))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
