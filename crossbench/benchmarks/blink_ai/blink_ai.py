# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import logging
from typing import TYPE_CHECKING, ClassVar, Sequence

from typing_extensions import override

from crossbench.action_runner.action.click import ClickAction
from crossbench.action_runner.action.position import PositionConfig
from crossbench.benchmarks.base import PressBenchmark, \
    PressBenchmarkStoryFilter
from crossbench.benchmarks.loading.input_source import InputSource
from crossbench.flags.chrome import ChromeFlags
from crossbench.helper import url_helper
from crossbench.stories.press_benchmark import PressBenchmarkStory

from .probe import BlinkAIProbe

if TYPE_CHECKING:
  from crossbench.benchmarks.base import VersionParts
  from crossbench.browsers.attributes import BrowserAttributes
  from crossbench.flags.base import Flags
  from crossbench.runner.run import Run


class BlinkAIStory(PressBenchmarkStory):
  NAME: ClassVar[str] = "blink_ai"
  URL: ClassVar[str] = "https://chromium-workloads.web.app/blink-ai/main/"
  URL_OFFICIAL: ClassVar[str] = (
      "https://chromium-workloads.web.app/blink-ai/main/")
  URL_LOCAL: ClassVar[str] = "http://localhost:8000/"
  SUBSTORIES: ClassVar[tuple[str, ...]] = (
      "language_model",
      "multimodal_image",
      "multimodal_images",
      "multimodal_audio",
  )

  @classmethod
  @override
  def default_story_names(cls) -> tuple[str, ...]:
    return ("language_model",)

  def __init__(self,
               substories: Sequence[str] = (),
               url: str | None = None) -> None:
    if not substories:
      substories = self.SUBSTORIES
    super().__init__(substories=substories, url=url or self.URL)

  @property
  @override
  def substory_duration(self) -> dt.timedelta:
    return dt.timedelta(seconds=15)

  @property
  @override
  def slow_duration(self) -> dt.timedelta:
    return dt.timedelta(minutes=15)

  @override
  def get_run_url(self, run: Run) -> str:
    url = super().get_run_url(run)
    if self.substories:
      url = url_helper.update_url_query(url,
                                        {"stories": ",".join(self.substories)})
    return url

  @override
  def setup(self, run: Run) -> None:
    url = self.get_run_url(run)
    with run.actions("Setup") as actions:
      actions.show_url(url)
      logging.info("Waiting for window.LanguageModel to become available...")
      try:
        actions.wait_js_condition(
            "return !!window.LanguageModel && window.testStatus === 'waiting'",
            0.5,
            timeout=dt.timedelta(seconds=45))
      except Exception as e:
        raise RuntimeError("Built-in AI API (window.LanguageModel) failed to"
                           " initialize within 30 seconds.") from e

  @override
  def run(self, run: Run) -> None:
    with run.actions("Running benchmark") as actions:
      logging.info("Clicking #start-button to initiate AI E2E test...")
      # Chrome's Built-in AI API strictly requires a trusted user gesture
      # to download and compile on-device models.
      if run.browser.attributes().is_chromium_based:
        action = ClickAction(InputSource.DRIVER,
                             PositionConfig.parse_str("#start-button"))
      else:
        action = ClickAction(InputSource.JS,
                             PositionConfig.parse_str("#start-button"))
      run.action_runner.click(action)
      actions.wait_js_condition(
          "return window.testStatus !== 'running' && "
          "window.testStatus !== 'waiting';",
          0.5,
          timeout=self.slow_duration)

      status = actions.js("return window.testStatus;")
      if status != "success":
        raise ValueError(
            "Blink-AI Benchmark did not finish successfully. "
            f"Final testStatus: '{status}'. "
        )

      metrics = actions.js("return window.metrics;")
      if not metrics or not isinstance(metrics, dict):
        raise RuntimeError("Benchmark finished without metrics. Check for a "
                           "browser tab or Mojo IPC crash.")


class BlinkAIBenchmark(PressBenchmark):
  """
  Benchmark runner for Chrome Built-in on-device AI APIs.
  """
  NAME: ClassVar[str] = "blink-ai"
  DEFAULT_STORY_CLS = BlinkAIStory
  PROBES: ClassVar[tuple[type[BlinkAIProbe], ...]] = (BlinkAIProbe,)
  STORY_FILTER_CLS: ClassVar = PressBenchmarkStoryFilter

  @classmethod
  @override
  def short_base_name(cls) -> str:
    return "blink-ai"

  @classmethod
  @override
  def base_name(cls) -> str:
    return "blink-ai"

  @classmethod
  @override
  def version(cls) -> VersionParts:
    return ("main",)

  @classmethod
  @override
  def extra_flags(cls, browser_attributes: BrowserAttributes) -> Flags:
    flags: Flags = super().extra_flags(browser_attributes)
    if not browser_attributes.is_chromium_based:
      return flags

    chrome_flags = ChromeFlags(flags)
    logging.info("Injecting experimental built-in AI flags for Chrome...")
    for feature in (
        "EnableBlinkReceiverAI",
        "LanguageModelAPI",
        "AIPromptAPI",
        "OnDeviceModelLitertLmBackend",
        "OptimizationGuideOnDeviceModelMultimodal",
        "OnDeviceModelPerformanceParams:"
        "compatible_on_device_performance_classes/*",
        "AIWriterAPI",
        "AIRewriterAPI",
        "AIPromptAPIMultimodalInput",
        "AIPromptAPIMultimodalMultilingual",
    ):
      chrome_flags.features.enable(feature)
    chrome_flags.blink_features.enable("AIResponseStreaming")
    # Force device evaluation override to run without download gate block.
    chrome_flags.set("--optimization-guide-force-device-evaluation-override")
    return chrome_flags
