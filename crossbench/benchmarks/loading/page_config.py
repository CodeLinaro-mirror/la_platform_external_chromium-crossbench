# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime as dt
import logging
from typing import (TYPE_CHECKING, Any, Dict, Final, Iterator, List, Optional,
                    Sequence, Tuple, Type, cast)
from urllib import parse as urlparse

from crossbench import cli_helper, exception
from crossbench import path as pth
from crossbench.benchmarks.loading.action import (Action, ActionType,
                                                  ClickAction, GetAction,
                                                  ReadyState, WaitAction)
from crossbench.benchmarks.loading.input_source import InputSource
from crossbench.benchmarks.loading.page import PAGES
from crossbench.benchmarks.loading.playback_controller import \
    PlaybackController
from crossbench.browsers.secrets import SecretType
from crossbench.config import ConfigError, ConfigObject, ConfigParser


@dataclasses.dataclass(frozen=True)
class ActionBlock(ConfigObject):
  label: str = "default"
  index: int = 0
  actions: Tuple[Action, ...] = tuple()

  @classmethod
  def parse_str(cls: Type[ActionBlock], value: str) -> ActionBlock:
    raise NotImplementedError("Cannot create action blocks from strings")

  @classmethod
  def parse_other(cls: Type[ActionBlock], value: Any, **kwargs) -> ActionBlock:
    if isinstance(value, (tuple, list)):
      return cls.parse_sequence(value, **kwargs)
    return super().parse_other(value, **kwargs)

  @classmethod
  def parse_dict(  # pylint: disable=arguments-differ
      cls: Type,
      config: Dict[str, Any],
      label: Optional[str] = None,
      index: Optional[int] = None):
    return cls.config_parser().parse(config, label=label, index=index)

  @classmethod
  def config_parser(cls: Type[ActionBlock]) -> ConfigParser[ActionBlock]:
    parser = ConfigParser(f"{cls.__name__} parser", cls)
    parser.add_argument("label", type=cls._parse_block_label, default="default")
    parser.add_argument(
        "index",
        type=cli_helper.parse_positive_zero_int,
        default=0,
        required=False)
    # TODO: enable passing index
    parser.add_argument("actions", type=Action, required=True, is_list=True)
    return parser

  @classmethod
  def parse_sequence(cls: Type[ActionBlock],
                     config: Sequence[Dict[str, Any]],
                     label: Optional[str] = None,
                     index: Optional[int] = None) -> ActionBlock:
    with exception.annotate_argparsing(
        "Parsing default block action sequence:"):
      return cls.parse_dict({"actions": config}, label=label, index=index)

  @classmethod
  def _parse_block_label(cls, value: Any) -> Optional[str]:
    if not value:
      return None
    label = cli_helper.parse_non_empty_str(value)
    if label == LoginBlock.LABEL:
      raise ConfigError(
          f"Block label {repr(label)} is reserved for login blocks")
    return value

  def validate(self) -> None:
    super().validate()
    cli_helper.parse_non_empty_sequence(self.actions, "actions")
    # TODO: enable validating action indices
    # for index, action in enumerate(self.actions):
    #   if index != action.index:
    #     raise ValueError(
    #         f"action[{index}].index should be {index}, but got {action.index}")
    if not self.actions:
      raise argparse.ArgumentTypeError("Invalid block without actions")

  def to_json(self) -> Dict[str, Any]:
    return {
        "label": self.label,
        "actions": [action.to_json() for action in self.actions]
    }

  @property
  def duration(self) -> dt.timedelta:
    total_duration = dt.timedelta()
    for action in self.actions:
      if duration := action.duration:
        total_duration += duration
    return total_duration

  @property
  def is_login(self) -> bool:
    return False

  def __iter__(self) -> Iterator[Action]:
    yield from self.actions

  def __len__(self) -> int:
    return len(self.actions)


@dataclasses.dataclass(frozen=True)
class LoginBlock(ActionBlock):
  LABEL: Final[str] = "login"

  def validate(self):
    super().validate()
    assert self.index == 0, (
        f"Login block has to be the first, but got {self.index}")

  @property
  def is_login(self) -> bool:
    return True


@dataclasses.dataclass(frozen=True)
class ActionBlockListConfig(ConfigObject):
  blocks: Tuple[ActionBlock, ...] = tuple()

  def to_argument_value(self) -> Tuple[ActionBlock, ...]:
    return self.blocks

  @classmethod
  def parse_other(cls: Type[ActionBlockListConfig],
                  value: Any) -> ActionBlockListConfig:
    if isinstance(value, (tuple, list)):
      return cls.parse_sequence(value)
    return super().parse_other(value)

  @classmethod
  def parse_sequence(cls: Type[ActionBlockListConfig],
                     config: Sequence[Dict[str, Any]]) -> ActionBlockListConfig:
    """Parse either a sequence of blocks or a sequence of actions for an
    implicit default block.

    Blocks:
    [{ "label": "block 1", "actions": [...]}, ... ]
    [ "block 1": [{ "action": ...}, ...], "block 2": [ ... ] ]

    Default block actions:
    [{ "action": "get", ...}, { "action": ...}, ...]
    """
    config = cli_helper.parse_non_empty_sequence(config, "actions")
    info = "action block"
    if cls._is_default_block_actions(config):
      info = "default actions"
      config = [{"actions": config}]
    if not cls._is_block_sequence_config(config):
      raise ValueError(
          "Invalid data: Expected a list of either blocks or actions.")

    def block_config_data_gen():
      for index, block_config in enumerate(config):
        with exception.annotate_argparsing(f"Parsing {info} ...[{index}]"):
          block_config = cli_helper.parse_dict(block_config, f"blocks[{index}]")
          label = block_config.get("label")
          yield index, label, block_config

    return cls._parse_blocks(block_config_data_gen())

  @classmethod
  def _is_block_sequence_config(cls, config: Sequence[Dict[str, Any]]) -> bool:
    return "label" in config[0] or "actions" in config[0]

  @classmethod
  def _is_default_block_actions(cls, config: Sequence[Dict[str, Any]]) -> bool:
    sample = config[0]
    return isinstance(sample, str) or "action" in sample

  @classmethod
  def parse_dict(cls: Type[ActionBlockListConfig],
                 config: Dict[str, Any]) -> ActionBlockListConfig:
    config = cli_helper.parse_non_empty_dict(config, "blocks")

    def block_config_data_gen():
      for index, (label, block_data) in enumerate(config.items()):
        with exception.annotate_argparsing(
            f"Parsing action block  ...[{label}]"):
          yield index, label, block_data

    return cls._parse_blocks(block_config_data_gen())

  @classmethod
  def _parse_blocks(cls, block_config_data_gen) -> ActionBlockListConfig:
    blocks: List[ActionBlock] = []
    for index, label, block_data in block_config_data_gen:
      block = cls._parse_block(index, label, block_data)
      blocks.append(block)
    return cls(tuple(blocks))

  @classmethod
  def _parse_block(cls, index: int, label: str, block_data: Any) -> ActionBlock:
    if isinstance(block_data, dict):
      # Early warning for better usability.
      if inner_label := block_data.get("label"):
        if inner_label != label:
          raise ConfigError(
              "ActionBlock inside a dict cannot have a 'label' property, "
              f"but got label={repr(inner_label)}")
    return ActionBlock.parse(block_data, label=label, index=index)

  @classmethod
  def parse_str(cls, value: str) -> ActionBlockListConfig:
    raise NotImplementedError("Cannot create action blocks from strings")

  def validate(self) -> None:
    super().validate()
    if not self.blocks:
      raise ValueError("Missing action blocks.")
    cli_helper.parse_non_empty_sequence(self.blocks, "blocks")
    found_get = False
    for index, block in enumerate(self.blocks):
      if index != block.index:
        raise ValueError(
            f"blocks[{index}].index should be {index}, but got {block.index}")
      found_get |= any(action.TYPE == ActionType.GET for action in block)
    if not found_get:
      raise ValueError("Expected at least one get action in one of the blocks.")


@dataclasses.dataclass(frozen=True)
class PageConfig(ConfigObject):
  label: Optional[str] = None
  playback: Optional[PlaybackController] = None
  blocks: Tuple[ActionBlock, ...] = tuple()
  login: Optional[LoginBlock] = None

  @classmethod
  def parse_other(cls: Type[PageConfig], value: Any, **kwargs) -> PageConfig:
    if isinstance(value, (list, tuple)):
      return cls.parse_sequence(value, **kwargs)
    return super().parse_other(value)

  @classmethod
  def parse_str(  # pylint: disable=arguments-differ
      cls: Type[PageConfig],
      value: str,
      label: Optional[str] = None) -> PageConfig:
    """
    Simple comma-separated string with optional duration:
      value = URL,[DURATION]
    """
    parts = value.rsplit(",", maxsplit=1)
    duration = dt.timedelta()
    raw_url: str = parts[0]
    if raw_url in PAGES:
      url = PAGES[raw_url].url
      label = label or raw_url
    else:
      url = cli_helper.parse_fuzzy_url_str(raw_url)
    if len(parts) == 2:
      duration = cli_helper.Duration.parse_non_zero(parts[1])
    return cls.from_url(label, url, duration)

  @classmethod
  def parse_sequence(cls: Type[PageConfig],
                     value: Sequence[Any],
                     label: Optional[str] = None) -> PageConfig:
    value = cli_helper.parse_non_empty_sequence(value,
                                                "story actions or blocks")
    blocks = ActionBlockListConfig.parse_sequence(value)
    if label is not None:
      label = cli_helper.parse_non_empty_str(label, "label")
    return cls(label, blocks=blocks.blocks)

  @classmethod
  def parse_dict(  # pylint: disable=arguments-differ
      cls: Type[PageConfig],
      config: Dict[str, Any],
      label: Optional[str] = None) -> PageConfig:
    config = cli_helper.parse_non_empty_dict(config, "story actions or blocks")
    page_config = cls.config_parser().parse(config, label=label)
    return page_config

  @classmethod
  def config_parser(cls: Type[PageConfig]) -> ConfigParser[PageConfig]:
    parser = ConfigParser(f"{cls.__name__} parser", cls)
    parser.add_argument("label", type=cli_helper.parse_non_empty_str)
    parser.add_argument("playback", type=PlaybackController.parse)
    parser.add_argument(
        "blocks",
        aliases=("actions", "url", "urls"),
        type=ActionBlockListConfig)
    parser.add_argument("login", type=LoginBlock.parse)
    return parser

  @classmethod
  def from_url(cls,
               label: Optional[str],
               url: str,
               duration: dt.timedelta = dt.timedelta()) -> PageConfig:
    actions = (GetAction(url, duration=duration),)
    blocks = (ActionBlock(actions=actions),)
    return PageConfig(label=label, blocks=blocks)

  def actions(self) -> Iterator[Action]:
    for block in self.blocks:
      yield from block

  @property
  def duration(self) -> dt.timedelta:
    return sum((action.duration for action in self.actions()), dt.timedelta())

  @property
  def any_label(self) -> str:
    return self.label or self.url_label

  @property
  def url_label(self) -> str:
    url = urlparse.urlparse(self.first_url)
    if url.scheme == "about":
      return url.path
    if url.scheme == "file":
      return pth.LocalPath(url.path).name
    if hostname := url.hostname:
      if hostname.startswith("www."):
        return hostname[len("www."):]
      return hostname
    return str(url)

  @property
  def first_url(self) -> str:
    for action in self.actions():
      if action.TYPE == ActionType.GET:
        return cast(GetAction, action).url
    raise RuntimeError("No GET action with an URL found.")

@dataclasses.dataclass(frozen=True)
class PagesConfig(ConfigObject):
  pages: Tuple[PageConfig, ...] = ()
  logins: Tuple[SecretType, ...] = ()

  def validate(self) -> None:
    super().validate()
    for index, page in enumerate(self.pages):
      assert isinstance(page, PageConfig), (
          f"pages[{index}] is not a PageConfig but {type(page).__name__}")

  @classmethod
  def parse_str(cls, value: str) -> PagesConfig:
    """
    Simple comma-separate config:
    value = URL, [DURATION], ...
    """
    values: List[str] = []
    previous_part: Optional[str] = None
    for part in value.strip().split(","):
      part = cli_helper.parse_non_empty_str(part, "url or duration")
      try:
        cli_helper.Duration.parse_non_zero(part)
        if not previous_part:
          raise argparse.ArgumentTypeError(
              "Duration can only follow after url. "
              f"Current value: {repr(part)}")
        values[-1] = f"{previous_part},{part}"
        previous_part = None
      except cli_helper.DurationParseError:
        previous_part = part
        values.append(part)
    return cls.parse_sequence(values)

  @classmethod
  def parse_unknown_path(cls, path: pth.LocalPath, **kwargs) -> PagesConfig:
    # Make sure we get errors for invalid files.
    return cls.parse_config_path(path, **kwargs)

  @classmethod
  def parse_other(cls, value: Any, **kwargs) -> PagesConfig:
    if isinstance(value, (list, tuple)):
      return cls.parse_sequence(value, **kwargs)
    return super().parse_other(value, **kwargs)

  @classmethod
  def parse_sequence(cls, values: Sequence[str]) -> PagesConfig:
    """
    Variant a): List of comma-separate URLs
      [ "URL,[DURATION]", ... ]
    """
    # TODO: support parsing a list of PageConfig dicts
    if not values:
      raise argparse.ArgumentTypeError("Got empty page list.")
    pages: List[PageConfig] = []
    for index, single_line_config in enumerate(values):
      with exception.annotate_argparsing(
          f"Parsing pages[{index}]: {repr(single_line_config)}"):
        pages.append(PageConfig.parse_str(single_line_config))
    return PagesConfig(pages=tuple(pages))

  @classmethod
  def parse_dict(cls, config: Dict) -> PagesConfig:
    """
    Variant a):
    { "pages": { "LABEL": PAGE_CONFIG }}
    """
    with exception.annotate_argparsing("Parsing stories"):
      if "pages" not in config:
        raise argparse.ArgumentTypeError(
            "Config does not provide a 'pages' dict.")
      pages = cli_helper.parse_non_empty_dict(config["pages"], "pages")
      with exception.annotate_argparsing("Parsing config 'pages'"):
        logins = [SecretType.parse(login) for login in config.get("logins", [])]
        pages = cls._parse_pages(pages)
        return PagesConfig(pages, tuple(logins))
    raise exception.UnreachableError()

  @classmethod
  def _parse_pages(cls, data: Dict[str, Any]) -> Tuple[PageConfig, ...]:
    pages = []
    for name, page_config in data.items():
      with exception.annotate_argparsing(f"Parsing story ...['{name}']"):
        page = PageConfig.parse(page_config, label=name)
        pages.append(page)
    return tuple(pages)


class DevToolsRecorderPagesConfig(PagesConfig):

  @classmethod
  def parse_str(cls: Type[PagesConfig], value: str) -> PagesConfig:
    raise NotImplementedError()

  @classmethod
  def parse_dict(cls, config: Dict[str, Any]) -> DevToolsRecorderPagesConfig:
    config = cli_helper.parse_non_empty_dict(config)
    with exception.annotate_argparsing("Loading DevTools recording file"):
      title = cli_helper.parse_non_empty_str(config["title"], "title")
      actions = cls._parse_steps(config["steps"])
      # Use default block
      blocks = (ActionBlock(actions=actions),)
      pages = (PageConfig(label=title, blocks=blocks),)
      return DevToolsRecorderPagesConfig(pages)
    raise exception.UnreachableError()

  @classmethod
  def _parse_steps(cls, steps: List[Dict[str, Any]]) -> Tuple[Action, ...]:
    actions: List[Action] = []
    for step in steps:
      maybe_actions: Optional[Action] = cls._parse_step(step)
      if maybe_actions:
        actions.append(maybe_actions)
        # TODO(cbruni): make this configurable
        actions.append(WaitAction(duration=dt.timedelta(seconds=1)))
    return tuple(actions)

  @classmethod
  def _parse_step(cls, step: Dict[str, Any]) -> Optional[Action]:
    step_type: str = step["type"]
    default_timeout = dt.timedelta(seconds=10)
    if step_type == "navigate":
      return GetAction(  # type: ignore
          step["url"], ready_state=ReadyState.COMPLETE)
    if step_type == "click":
      selectors: List[List[str]] = step["selectors"]
      xpath: Optional[str] = None
      for selector_list in selectors:
        for selector in selector_list:
          if selector.startswith("xpath//"):
            xpath = selector
            break
      assert xpath, "Need xpath selector for click action"
      return ClickAction(
          InputSource.JS,
          selector=xpath,
          scroll_into_view=True,
          timeout=default_timeout)
    if step_type == "setViewport":
      # Resizing is ignored for now.
      return None
    raise ValueError(f"Unsupported step: {step_type}")


class ListPagesConfig(PagesConfig):

  VALID_EXTENSIONS: Tuple[str, ...] = (".txt", ".list")

  @classmethod
  def parse_str(cls, value: str) -> PagesConfig:
    raise argparse.ArgumentTypeError(
        f"URL list file {repr(value)} does not exist.")

  @classmethod
  def parse_path(cls, path: pth.LocalPath, **kwargs) -> PagesConfig:
    assert not kwargs, f"{cls.__name__} does not support extra kwargs"
    pages: List[PageConfig] = []
    with exception.annotate_argparsing(f"Loading Pages list file: {path.name}"):
      line: int = 0
      with path.open() as f:
        for single_line_config in f.readlines():
          with exception.annotate_argparsing(f"Parsing line {line}"):
            line += 1
            single_line_config = single_line_config.strip()
            if not single_line_config:
              logging.warning("Skipping empty line %s", line)
              continue
            pages.append(PageConfig.parse(single_line_config))
    return PagesConfig(pages=tuple(pages))

  @classmethod
  def parse_dict(cls, config: Dict) -> PagesConfig:
    config = cli_helper.parse_non_empty_dict(config, "pages")
    with exception.annotate_argparsing("Parsing scenarios / pages"):
      if "pages" not in config:
        raise argparse.ArgumentTypeError(
            "Config does not provide a 'pages' dict.")
      pages = config["pages"]
      if isinstance(pages, str):
        pages = [pages]
      if not isinstance(pages, (list, tuple)):
        raise argparse.ArgumentTypeError(
            f"Expected list/tuple for pages, but got {type(pages)}")
      return cls.parse_sequence(pages)
    raise exception.UnreachableError()
