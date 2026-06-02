# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
from typing import TYPE_CHECKING, ClassVar, cast

from typing_extensions import override

from crossbench.benchmarks.benchmark_probe import BenchmarkProbeMixin
from crossbench.probes.json import JsonResultProbe, JsonResultProbeContext
from crossbench.probes.metric import MetricsMerger

if TYPE_CHECKING:
  from crossbench.browsers.browser import Browser
  from crossbench.probes.results import ProbeResult
  from crossbench.runner.actions import Actions
  from crossbench.runner.groups.browsers import BrowsersRunGroup
  from crossbench.runner.groups.stories import StoriesRunGroup
  from crossbench.runner.run import Run
  from crossbench.types import Json


class BlinkAIProbe(BenchmarkProbeMixin, JsonResultProbe):
  """
  Custom probe for Blink AI benchmark.
  Extracts window.metrics from the browser tab.
  """
  NAME: ClassVar[str] = "blink_ai"

  @override
  def attach(self, browser: Browser) -> None:
    super().attach(browser)
    for flag in (
        "--disable-component-update",
        "--disable-optimization-guide-model-downloads-for-benchmarking"):
      browser.flags.pop(flag, None)

  @override
  def create_context(self, run: Run) -> BlinkAIProbeContext:
    return cast(BlinkAIProbeContext, super().create_context(run))

  @override
  def get_context_cls(self) -> type[BlinkAIProbeContext]:
    return BlinkAIProbeContext

  @override
  def merge_stories(self, group: StoriesRunGroup) -> ProbeResult:
    merged = MetricsMerger.merge_json_list(
        repetitions_group.results[self].json
        for repetitions_group in group.repetitions_groups)
    return self.write_group_result(group, merged)

  @override
  def merge_browsers(self, group: BrowsersRunGroup) -> ProbeResult:
    return self.merge_browsers_json_list(group).merge(
        self.merge_browsers_csv_list(group))


class BlinkAIProbeContext(JsonResultProbeContext[BlinkAIProbe]):
  JS: ClassVar[str] = "return JSON.stringify(window.metrics || {});"

  @override
  def to_json(self, actions: Actions) -> Json:
    if json_payload := actions.js(self.JS):
      return json.loads(json_payload)
    return {}
