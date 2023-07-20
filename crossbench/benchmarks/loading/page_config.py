# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional, TextIO, TypeVar

import datetime as dt

import hjson

from crossbench import cli_helper
from crossbench.benchmarks.loading.playback_controller import \
    PlaybackController
from crossbench.exception import ExceptionAnnotator

from . import action
from .page import InteractivePage


class AbstractPageConfig(abc.ABC):

  @classmethod
  def parse(cls, path: str) -> List[InteractivePage]:
    config_file = cli_helper.parse_file_path(path)
    with config_file.open(encoding="utf-8") as f:
      config = cls()
      config.load(f)
      return config.stories

  def __init__(self, raw_config_data: Optional[Dict] = None):
    self._exceptions = ExceptionAnnotator(throw=True)
    self.stories: List[InteractivePage] = []
    if raw_config_data:
      self.load_dict(raw_config_data)

  def load(self, f: TextIO, throw: bool = False) -> None:
    assert not self.stories
    self._exceptions.throw = throw
    with self._exceptions.capture(f"Loading Pages config file: {f.name}"):
      with self._exceptions.info(f"Parsing {hjson.__name__}"):
        config = hjson.load(f)
        self.load_dict(config, throw=throw)
    self._exceptions.assert_success()

  def load_dict(self, config: Dict[str, Any], throw: bool = False) -> None:
    assert not self.stories
    self._exceptions.throw = throw
    self._load_dict(config)
    self._exceptions.assert_success()

  @abc.abstractmethod
  def _load_dict(self, raw_config_data: Dict) -> None:
    pass


ActionT = TypeVar("ActionT", bound=action.Action)


class PageConfig(AbstractPageConfig):

  def _load_dict(self, raw_config_data: Dict) -> None:
    with self._exceptions.capture("Parsing scenarios / pages"):
      if "pages" not in raw_config_data:
        raise ValueError("Config does not provide a 'pages' dict.")
      if not raw_config_data["pages"]:
        raise ValueError("Config contains empty 'pages' dict.")
      with self._exceptions.info("Parsing config 'pages'"):
        self._parse_pages(raw_config_data["pages"])

  def _parse_pages(self, pages: Dict[str, Any]) -> None:
    """
    Behaviour to be aware

    There's no default Actions. In other words, if there's no Actions
    for a scenario this specific scenario will be ignored since there's
    nothing to do.

    If one would want to simply navigate to a site it is important to at
    least include: {action: "GET", value/url: google.com} in the specific
    scenario.

    As an example look at: page.config.example.hjson
    """
    playback: PlaybackController = PlaybackController.parse(
        pages.get("playback", "1x"))
    for scenario_name, actions in pages.items():
      with self._exceptions.info(f"Parsing scenario ...['{scenario_name}']"):
        actions = self._parse_actions(actions, scenario_name)
        self.stories.append(InteractivePage(actions, scenario_name, playback))

  def _parse_actions(self, actions: List[Dict[str, Any]],
                     scenario_name: str) -> List[action.Action]:
    if not actions:
      raise ValueError(f"Scenario '{scenario_name}' has no action")
    if not isinstance(actions, list):
      raise ValueError(f"Expected list, got={type(actions)}, '{actions}'")
    actions_list: List[action.Action] = []
    get_action_found = False
    for i, step in enumerate(actions):
      with self._exceptions.info(f"Parsing action ...['{scenario_name}'][{i}]"):
        if step.get("action") == action.ActionType.GET:
          get_action_found = True
        if "action" not in step:
          raise ValueError("No 'action' property found.")
        action_type = step["action"]
        if not action_type:
          raise ValueError("Empty 'action' property")
        action_duration = cli_helper.Duration.parse(step.get("duration", 0.0))
        value = step.get("url") or step.get("value")
        actions_list.append(
            self._create_action(action_type, value, action_duration))
    assert get_action_found, ("Not a valid entry for scenario: "
                              f"{scenario_name}. No 'get' action found.")
    assert actions_list, (f"Not valid entry for scenario {scenario_name} "
                          "does not contain any valid actions")
    return actions_list

  def _create_action(self, action_type: action.ActionType, value,
                     duration: dt.timedelta) -> ActionT:
    if action_type not in action.ACTION_FACTORY:
      raise ValueError(f"Unknown action name: '{action_type}'")
    return action.ACTION_FACTORY[action_type](value, duration)


class DevToolsRecorderPageConfig(AbstractPageConfig):

  def _load_dict(self, raw_config_data: Dict) -> None:
    playback: PlaybackController = PlaybackController.once()
    with self._exceptions.capture("Loading DevTools recording file"):
      title = raw_config_data["title"]
      assert title, "No title provided"
      actions = self._parse_steps(raw_config_data["steps"])
      self.stories.append(InteractivePage(actions, title, playback))

  def _parse_steps(self, steps: List[Dict[str, Any]]) -> List[action.Action]:
    actions: List[action.Action] = []
    for step in steps:
      maybe_actions: Optional[action.Action] = self._parse_step(step)
      if maybe_actions:
        actions.append(maybe_actions)
        # TODO(cbruni): make this configurable
        actions.append(action.WaitAction(duration=dt.timedelta(seconds=1)))
    return actions

  def _parse_step(self, step: Dict[str, Any]) -> Optional[action.Action]:
    step_type: str = step["type"]
    default_timeout = dt.timedelta(seconds=10)
    if step_type == "navigate":
      return action.GetAction(    # type: ignore
          step["url"], default_timeout, ready_state=action.ReadyState.COMPLETE)
    if step_type == "click":
      selectors: List[List[str]] = step["selectors"]
      xpath: Optional[str] = None
      for selector_list in selectors:
        for selector in selector_list:
          if selector.startswith("xpath//"):
            xpath = selector
            break
      assert xpath, "Need xpath selector for click action"
      return action.ClickAction(xpath, default_timeout, scroll_into_view=True)
    if step_type == "setViewport":
      # Resizing is ignored for now.
      return None
    raise ValueError(f"Unsupported step: {step_type}")
