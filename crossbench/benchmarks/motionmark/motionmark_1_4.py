# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import itertools
from typing import TYPE_CHECKING, ClassVar

from typing_extensions import override

from crossbench.benchmarks.motionmark.motionmark_1 import \
    MotionMark1Benchmark, MotionMark1Probe, MotionMark1ProbeContext, \
    MotionMark1Story

if TYPE_CHECKING:
  from crossbench.benchmarks.base import VersionParts
  from crossbench.runner.actions import Actions
  from crossbench.runner.run import Run


class MotionMark14Probe(MotionMark1Probe):
  __doc__ = MotionMark1Probe.__doc__
  NAME: ClassVar = "motionmark_1.4"

  @override
  def get_context_cls(self) -> type[MotionMark14ProbeContext]:
    return MotionMark14ProbeContext


class MotionMark14ProbeContext(MotionMark1ProbeContext):
  JS: ClassVar[str] = """
    const runnerClient = window.benchmarkController?.runnerClient ||
        window.benchmarkRunnerClient;
    const calculator = runnerClient?.scoreCalculator || runnerClient?.results;
    return calculator?.results;
  """


class MotionMark14Story(MotionMark1Story):
  NAME: ClassVar = "motionmark_1.4"
  URL: ClassVar[
      str] = "https://chromium-workloads.web.app/motionmark/v1.4/MotionMark"
  URL_OFFICIAL: ClassVar[str] = "https://browserbench.org/MotionMark1.4"
  READY_TIMEOUT: ClassVar[dt.timedelta] = dt.timedelta(seconds=12)
  DEVELOPER_READY_JS: ClassVar[str] = (
      "return !(document.querySelector('#frame-rate-detection span'));")
  READY_JS: ClassVar[str] = (
      "return !!("
      "   document.querySelector('#frame-rate-label')?.textContent?.trim());")
  ALL_STORIES: ClassVar = {
      "MotionMark": (
          "Stories",
          "Alice",
          "Chess",
          "Map Zoomer",
          "Sheets",
          "Départements",
          "Dashboard",
          "Filtering",
      ),
      "HTML suite":
          MotionMark1Story.ALL_STORIES["HTML suite"],
      "Canvas suite":
          MotionMark1Story.ALL_STORIES["Canvas suite"],
      "SVG suite":
          MotionMark1Story.ALL_STORIES["SVG suite"],
      "Leaves suite":
          MotionMark1Story.ALL_STORIES["Leaves suite"],
      "Multiply suite":
          MotionMark1Story.ALL_STORIES["Multiply suite"],
      "Text suite":
          MotionMark1Story.ALL_STORIES["Text suite"],
      "Suits suite":
          MotionMark1Story.ALL_STORIES["Suits suite"],
      "3D Graphics":
          MotionMark1Story.ALL_STORIES["3D Graphics"],
      "Basic canvas path suite":
          (MotionMark1Story.ALL_STORIES["Basic canvas path suite"]),
  }
  SUBSTORIES: ClassVar = tuple(
      itertools.chain.from_iterable(ALL_STORIES.values()))

  @override
  def _setup_filter_stories(self, actions: Actions) -> None:
    num_enabled = actions.js(
        """
        const benchmarks = arguments[0];
        let counter = 0;
        for (const suiteElement of window.suitesManager._suitesElements()) {
          const suiteCheckbox =
              window.suitesManager._checkboxElement(suiteElement);
          for (const testElement of suiteCheckbox.testsElements) {
            const testCheckbox =
                window.suitesManager._checkboxElement(testElement);
            testCheckbox.checked = false;
          }
        }
        for (const suiteElement of window.suitesManager._suitesElements()) {
          const suiteCheckbox =
              window.suitesManager._checkboxElement(suiteElement);
          if (suiteCheckbox.suite.name === "Tentative 1.4 suite") {
            continue;
          }
          for (const testElement of suiteCheckbox.testsElements) {
            const testCheckbox =
                window.suitesManager._checkboxElement(testElement);
            if (benchmarks.includes(testCheckbox.test.name)) {
              testCheckbox.checked = true;
              counter++;
            }
          }
          window.suitesManager._updateSuiteCheckboxState(suiteCheckbox);
        }
        window.benchmarkController.updateStartButtonState();
        return counter;
        """,
        arguments=[self._substories])
    assert num_enabled > 0, f"No tests were enabled for {self._substories}"
    actions.wait(0.1)

  @override
  def run(self, run: Run) -> None:
    with run.actions("Running") as actions:
      actions.js("window.benchmarkController.startBenchmark()")
      actions.wait(self.fast_duration)
    with run.actions("Waiting for completion") as actions:
      actions.wait_js_condition(
          """
          const runnerClient = window.benchmarkController?.runnerClient ||
              window.benchmarkRunnerClient;
          const calculator = runnerClient?.scoreCalculator ||
              runnerClient?.results;
          return Boolean(calculator?._results);
          """,
          0.5,
          timeout=self.slow_duration,
          delay=self.substory_duration / 4)


class MotionMark14Benchmark(MotionMark1Benchmark):
  """
  Benchmark runner for MotionMark 1.4.

  See https://browserbench.org/MotionMark1.4/ for more details.
  """

  NAME: ClassVar = "motionmark_1.4"
  DEFAULT_STORY_CLS: ClassVar = MotionMark14Story
  PROBES: ClassVar = (MotionMark14Probe,)

  @classmethod
  @override
  def version(cls) -> VersionParts:
    return (1, 4)
