# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import logging
from typing import TYPE_CHECKING, ClassVar, Final, Self, Sequence

from typing_extensions import override

from crossbench.action_runner.action.click import ClickAction
from crossbench.action_runner.action.position import PositionConfig
from crossbench.benchmarks.base import PressBenchmark, \
    PressBenchmarkStoryFilter
from crossbench.benchmarks.loading.input_source import InputSource
from crossbench.flags.chrome import ChromeFlags
from crossbench.helper import url_helper
from crossbench.parse import ObjectParser
from crossbench.stories.press_benchmark import PressBenchmarkStory

from .config.language_model import LANGUAGE_MODEL_API
from .config.registry import get_api_config
from .probe import BlinkAIProbe

if TYPE_CHECKING:
  from crossbench.benchmarks.base import VersionParts
  from crossbench.browsers.attributes import BrowserAttributes
  from crossbench.flags.base import Flags
  from crossbench.runner.run import Run
  from crossbench.stories.story import Story

  from .config.base import BlinkAIApiConfig


class BlinkAIStory(PressBenchmarkStory):
  NAME: ClassVar[str] = "blink_ai"
  URL: ClassVar[str] = "https://chromium-workloads.web.app/blink-ai/main/"
  URL_OFFICIAL: ClassVar[str] = (
      "https://chromium-workloads.web.app/blink-ai/main/")
  URL_LOCAL: ClassVar[str] = "http://localhost:8000/"
  SUBSTORIES: ClassVar[tuple[str, ...]] = LANGUAGE_MODEL_API.all_substory_names

  @classmethod
  @override
  def default_story_names(cls) -> tuple[str, ...]:
    return LANGUAGE_MODEL_API.default_substories

  @classmethod
  @override
  def all(cls,
          separate: bool = False,
          url: str | None = None,
          api_name: str = LANGUAGE_MODEL_API.name,
          **kwargs: object) -> tuple[Self, ...]:
    api_config = get_api_config(api_name)
    return cls.from_names(
        api_config.all_substory_names,
        separate=separate,
        url=url,
        api_name=api_name,
        **kwargs)

  @classmethod
  @override
  def default(cls,
              separate: bool = False,
              url: str | None = None,
              api_name: str = LANGUAGE_MODEL_API.name,
              **kwargs: object) -> tuple[Self, ...]:
    api_config = get_api_config(api_name)
    return cls.from_names(
        api_config.default_substories,
        separate=separate,
        url=url,
        api_name=api_name,
        **kwargs)

  def __init__(
      self,
      substories: Sequence[str] = (),
      url: str | None = None,
      api_name: str = LANGUAGE_MODEL_API.name,
      model: str | None = None,
  ) -> None:
    self._api_config: Final[BlinkAIApiConfig] = get_api_config(api_name)
    if model is not None:
      self._api_config.get_model_config(model)
    self._model: Final[str | None] = model
    if not substories:
      substories = self._api_config.default_substories
    super().__init__(substories=substories, url=url or self.URL)

  @property
  def api_config(self) -> BlinkAIApiConfig:
    return self._api_config

  @property
  def api_name(self) -> str:
    return self._api_config.name

  @property
  def model(self) -> str | None:
    return self._model

  @property
  def required_features(self) -> tuple[str, ...]:
    return self._api_config.resolve_features(self.substories, model=self._model)

  @property
  @override
  def has_default_substories(self) -> bool:
    return tuple(self.substories) == self._api_config.default_substories

  @override
  def _get_unique_name(self) -> str:
    substories_set = set(self._substories)
    if substories_set == set(self._api_config.default_substories):
      return self.api_name
    if substories_set == set(self._api_config.all_substory_names):
      return f"{self.api_name}_all"
    name = "_".join((self.api_name, *self._substories))
    return self._crop_name(name)

  @override
  def _verify_substories(self) -> None:
    ObjectParser.unique_sequence(self.substories, "substories", ValueError)
    for substory in self.substories:
      if substory == "all":
        raise ValueError("Substory name cannot be 'all'")
      self.verify_story_name(substory)
      self._api_config.resolve_model_name(substory, self._model)

  @property
  @override
  def substory_duration(self) -> dt.timedelta:
    return dt.timedelta(seconds=100)

  @property
  @override
  def slow_duration(self) -> dt.timedelta:
    return dt.timedelta(minutes=15)

  @property
  def url_params(self) -> dict[str, str]:
    return {
        "api": self.api_name,
        "stories": ",".join(self.substories),
    }

  @property
  @override
  def test_url(self) -> str:
    return url_helper.update_url_query(self.url, self.url_params)

  @override
  def get_run_url(self, run: Run) -> str:
    url = super().get_run_url(run)
    return url_helper.update_url_query(url, self.url_params)

  @override
  def setup(self, run: Run) -> None:
    url = self.get_run_url(run)
    js_global = self.api_config.js_global
    with run.actions("Setup") as actions:
      actions.show_url(url)
      logging.info("Waiting for window.%s to become available...", js_global)
      try:
        actions.wait_js_condition(
            f"return !!window.{js_global} && window.testStatus === 'waiting'",
            0.5,
            timeout=dt.timedelta(seconds=45))
      except Exception as e:
        raise RuntimeError(f"Built-in AI API (window.{js_global}) failed to"
                           " initialize within 45 seconds.") from e

  @override
  def run(self, run: Run) -> None:
    with run.actions("Running benchmark") as actions:
      logging.info("Clicking #start-button to initiate AI E2E test...")
      # Chrome's Built-in AI API strictly requires a trusted user gesture
      # to download and compile on-device models.
      if run.browser.attributes().is_chromium_based:
        input_source = InputSource.DRIVER
      else:
        input_source = InputSource.JS
      action = ClickAction.create(input_source,
                                  PositionConfig.parse_str("#start-button"))
      run.action_runner.click(action)
      actions.wait_js_condition(
          "return window.testStatus !== 'running' && "
          "window.testStatus !== 'waiting';",
          0.5,
          timeout=self.slow_duration)

      status = actions.js("return window.testStatus;")
      if status != "success":
        raise ValueError("Blink-AI Benchmark did not finish successfully. "
                         f"Final testStatus: '{status}'. ")

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
  def extra_flags(cls, browser_attributes: BrowserAttributes,
                  story: Story) -> Flags:
    flags: Flags = super().extra_flags(browser_attributes, story)
    if not browser_attributes.is_chromium_based:
      return flags

    chrome_flags = ChromeFlags(flags)
    assert isinstance(story, BlinkAIStory)
    logging.info("Injecting experimental built-in AI flags for Chrome...")
    for feature in story.required_features:
      chrome_flags.features.enable(feature)
    return chrome_flags
