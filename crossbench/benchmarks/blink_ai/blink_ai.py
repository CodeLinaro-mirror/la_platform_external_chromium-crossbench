# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt
import logging
from typing import TYPE_CHECKING, ClassVar, Final, Iterable, Self, Sequence

from ordered_set import OrderedSet
from typing_extensions import override

from crossbench.action_runner.action.click import ClickAction
from crossbench.action_runner.action.position import PositionConfig
from crossbench.benchmarks.base import PressBenchmark, \
    PressBenchmarkStoryFilter, RegexFilter
from crossbench.benchmarks.loading.input_source import InputSource
from crossbench.flags.chrome import ChromeFlags
from crossbench.helper import url_helper
from crossbench.parse import ObjectParser
from crossbench.stories.press_benchmark import PressBenchmarkStory

from .config import registry as blink_ai_registry
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


class BlinkAIStoryFilter(PressBenchmarkStoryFilter[BlinkAIStory]):
  """Filter Blink AI stories by API, model, and substory name or regexp.

  Examples:
    Single API (default --api=language_model):
      --stories=mtp_summary,multimodal_audio
      --api=writer --stories=short

    Multiple APIs (--api=language_model,writer or --api=all):
      --api=language_model,writer
      --api=all --stories=all
      --api=language_model,writer \
          --stories=language_model:mtp_summary,writer:short
      --api=language_model,writer --stories=writer:default,-writer:long
  """
  __doc__ = f"{PressBenchmarkStoryFilter.__doc__}\n{__doc__}"

  @classmethod
  def api_configs_help(cls) -> str:
    parts = [
        f"{api_name}: {', '.join(cfg.all_substory_names)}"
        for api_name, cfg in blink_ai_registry.API_CONFIGS.items()
    ]
    return "Available stories per API: " + "; ".join(parts)

  @classmethod
  def model_choices(cls) -> tuple[str, ...]:
    return tuple(
        OrderedSet(model for cfg in blink_ai_registry.API_CONFIGS.values()
                   for model in cfg.models))

  @classmethod
  def parse_api_names(cls, value: str | Sequence[str]) -> tuple[str, ...]:
    raw_names = OrderedSet(
        ObjectParser.unique_sequence(
            tuple(
                ObjectParser.non_empty_str(item, "api")
                for item in ObjectParser.str_tuple(value, "api")),
            "api",
            ValueError,
        ))
    if not raw_names:
      raise ValueError("Expected at least one API name.")
    if "all" in raw_names:
      if len(raw_names) > 1:
        raise ValueError(
            "Cannot combine 'all' with specific API names in --api.")
      return tuple(blink_ai_registry.API_CONFIGS)
    return tuple(get_api_config(name).name for name in raw_names)

  @classmethod
  @override
  def _add_story_grouping_arguments(
      cls, group: argparse._MutuallyExclusiveGroup) -> None:
    super()._add_story_grouping_arguments(group)
    group.set_defaults(separate=None)

  @classmethod
  @override
  def add_cli_arguments(
      cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    super().add_cli_arguments(parser)
    parser.add_argument(
        "--api",
        default=(LANGUAGE_MODEL_API.name,),
        type=cls.parse_api_names,
        help=("Comma-separated Built-in AI APIs to benchmark, or 'all'. "
              f"{cls.api_configs_help()}"))
    parser.add_argument(
        "--model",
        default=None,
        choices=cls.model_choices(),
        type=ObjectParser.non_empty_str,
        help="Model selector name for the selected API (e.g. 'default', 'v4').")
    return parser

  @classmethod
  @override
  def kwargs_from_cli(cls, args: argparse.Namespace) -> dict[str, object]:
    kwargs = super().kwargs_from_cli(args)
    api_names: tuple[str, ...] = cls.parse_api_names(args.api)
    separate: bool | None = args.separate
    if len(api_names) > 1:
      if args.model:
        raise argparse.ArgumentTypeError(
            "Cannot specify --model when multiple APIs are selected.")
      if separate is False:
        raise argparse.ArgumentTypeError(
            "Cannot use --combined when multiple APIs are selected.")
      separate = True
    elif separate is None:
      separate = False
    kwargs["separate"] = separate
    kwargs["api_names"] = api_names
    kwargs["model"] = args.model
    return kwargs

  def __init__(
      self,
      story_cls: type[BlinkAIStory],
      patterns: Sequence[str],
      args: argparse.Namespace,
      separate: bool = False,
      url: str | None = None,
      tags: Iterable[str] = (),
      api_names: Sequence[str] = (LANGUAGE_MODEL_API.name,),
      model: str | None = None,
  ) -> None:
    self._api_configs: Final[tuple[BlinkAIApiConfig, ...]] = tuple(
        get_api_config(name) for name in self.parse_api_names(api_names))
    if self._has_multiple_apis and not separate:
      raise ValueError(
          "Cannot combine stories when multiple APIs are selected; "
          "use separate=True (--separate).")
    if self._has_multiple_apis and model:
      raise ValueError(
          "Cannot specify --model when multiple APIs are selected.")
    if model:
      self._api_configs[0].get_model_config(model)
    self._model: Final[str | None] = model or None
    super().__init__(
        story_cls,
        patterns,
        args,
        separate=separate,
        url=url,
        tags=tags,
    )

  @property
  def _has_multiple_apis(self) -> bool:
    return len(self._api_configs) > 1

  def _split_api_pattern(self, pattern: str) -> tuple[str | None, str]:
    if ":" not in pattern:
      if self._has_multiple_apis and pattern not in ("default", "all"):
        raise ValueError(
            f"Unqualified story pattern {pattern!r} is ambiguous when "
            "multiple APIs are selected. Use '<api>:<pattern>' "
            "(e.g. 'language_model:mtp_summary,writer:short') or "
            "'default' / 'all'.")
      return None, pattern
    is_negative = pattern.startswith("-")
    raw = pattern[1:] if is_negative else pattern
    api_prefix, inner_pattern = raw.split(":", maxsplit=1)
    if not api_prefix or not inner_pattern:
      raise ValueError(f"Invalid API-qualified story pattern {pattern!r}. "
                       "Expected '<api>:<pattern>'.")
    api_config = get_api_config(api_prefix)
    if api_config not in self._api_configs:
      selected = ", ".join(cfg.name for cfg in self._api_configs)
      raise ValueError(
          f"Story pattern {pattern!r} targets API {api_config.name!r}, "
          f"which is not in selected --api={selected!r}.")
    if is_negative and not inner_pattern.startswith("-"):
      inner_pattern = f"-{inner_pattern}"
    return api_config.name, inner_pattern

  def _group_by_api(self, items: Sequence[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {cfg.name: [] for cfg in self._api_configs}
    for item in items:
      api_name, inner = self._split_api_pattern(item)
      if api_name:
        grouped[api_name].append(inner)
        continue
      for cfg in self._api_configs:
        grouped[cfg.name].append(inner)
    return grouped

  @override
  def filter_by_name(self, patterns: Sequence[str]) -> tuple[BlinkAIStory, ...]:
    if not isinstance(patterns, (list, tuple)):
      raise ValueError("Expected Sequence of story name or patterns "
                       f"but got {type(patterns)!r}.")
    per_api_patterns = self._group_by_api(patterns)
    stories: list[BlinkAIStory] = []
    for api_config in self._api_configs:
      if not (api_patterns := per_api_patterns[api_config.name]):
        continue
      regex_filter = RegexFilter(api_config.all_substory_names,
                                 api_config.default_substories)
      if not (selected_names := regex_filter.process_all(api_patterns)):
        continue
      stories.extend(self._stories_for_api(api_config, tuple(selected_names)))
    if not stories:
      raise ValueError("No stories matched the provided filter patterns.")
    return tuple(stories)

  def _stories_for_api(
      self,
      api_config: BlinkAIApiConfig,
      names: Sequence[str],
  ) -> tuple[BlinkAIStory, ...]:
    if not self.separate:
      api_config.validate_combined_substories(names, model=self._model)
    return self.story_cls.from_names(
        names,
        separate=self.separate,
        url=self.url,
        api_name=api_config.name,
        model=self._model,
    )

  @override
  def stories_from_names(self,
                         names: Sequence[str]) -> tuple[BlinkAIStory, ...]:
    if not names:
      raise ValueError("No substories provided")
    per_api_names = self._group_by_api(names)
    stories: list[BlinkAIStory] = []
    for api_config in self._api_configs:
      if not (api_substory_names := per_api_names[api_config.name]):
        continue
      stories.extend(self._stories_for_api(api_config, api_substory_names))
    if not stories:
      raise ValueError("No stories created from provided names.")
    return tuple(stories)


class BlinkAIBenchmark(PressBenchmark):
  """
  Benchmark runner for Chrome Built-in on-device AI APIs.
  """
  NAME: ClassVar[str] = "blink-ai"
  DEFAULT_STORY_CLS = BlinkAIStory
  PROBES: ClassVar[tuple[type[BlinkAIProbe], ...]] = (BlinkAIProbe,)
  STORY_FILTER_CLS: ClassVar[
      type[PressBenchmarkStoryFilter]] = BlinkAIStoryFilter

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
