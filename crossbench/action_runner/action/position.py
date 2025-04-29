# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import dataclasses
import functools
from typing import TYPE_CHECKING, Any, Dict, Self, Type

from typing_extensions import override

from crossbench.benchmarks.loading.point import Point
from crossbench.config import ConfigObject, ConfigParser, UnusedPropertiesMode
from crossbench.parse import NumberParser, ObjectParser

if TYPE_CHECKING:
  from crossbench.types import JsonDict


@dataclasses.dataclass(frozen=True)
class CoordinatesConfig(ConfigObject):
  x: int
  y: int

  @classmethod
  @override
  def parse_str(cls, value: str):
    del value
    raise NotImplementedError("Cannot create CoordinatesConfig from string")

  @classmethod
  @override
  @functools.lru_cache(maxsize=1)
  def config_parser(
      cls: Type[CoordinatesConfig]) -> ConfigParser[CoordinatesConfig]:
    parser = ConfigParser(
        cls, unused_properties_mode=UnusedPropertiesMode.ERROR)
    parser.add_argument("x", type=NumberParser.positive_zero_int, required=True)
    parser.add_argument("y", type=NumberParser.positive_zero_int, required=True)
    return parser

  def point(self) -> Point:
    return Point(self.x, self.y)


@dataclasses.dataclass(frozen=True)
class SelectorConfig(ConfigObject):
  selector: str

  required: bool
  scroll_into_view: bool
  wait: bool

  @classmethod
  @override
  def parse_str(cls, value: str) -> Self:
    selector = ObjectParser.non_empty_str(value, "selector")
    return cls(
        selector=selector, required=True, scroll_into_view=False, wait=False)

  @classmethod
  @override
  @functools.lru_cache(maxsize=1)
  def config_parser(cls: Type[SelectorConfig]) -> ConfigParser[SelectorConfig]:
    parser = ConfigParser(
        cls, unused_properties_mode=UnusedPropertiesMode.ERROR)
    parser.add_argument(
        "selector", type=ObjectParser.non_empty_str, required=True)
    parser.add_argument("required", type=ObjectParser.bool, default=True)
    parser.add_argument(
        "scroll_into_view", type=ObjectParser.bool, default=False)
    parser.add_argument("wait", type=ObjectParser.bool, default=False)
    return parser


@dataclasses.dataclass(frozen=True)
class UiSelectorConfig(ConfigObject):
  res: str

  @classmethod
  @override
  def parse_str(cls, value) -> UiSelectorConfig:
    del value
    raise NotImplementedError("Cannot create UiSelectorConfig from string")

  @classmethod
  @override
  def parse_dict(cls, config: dict[str, Any],
                 **kwargs: Any) -> UiSelectorConfig:
    return cls.config_parser().parse(config)

  @classmethod
  @override
  def config_parser(cls) -> ConfigParser[UiSelectorConfig]:
    parser = ConfigParser(
        cls, unused_properties_mode=UnusedPropertiesMode.ERROR)
    parser.add_argument(
        "res", type=ObjectParser.non_empty_str, required=True,
        help="Resource name of the UI element to match.")
    return parser


@dataclasses.dataclass(frozen=True)
class PositionConfig(ConfigObject):
  coordinates: CoordinatesConfig | None = None
  selector: SelectorConfig | None = None
  ui_selector: UiSelectorConfig | None = None

  @classmethod
  @override
  def parse_str(cls, value: str) -> Self:
    return cls(selector=SelectorConfig.parse_str(value))

  @classmethod
  @override
  def parse_dict(cls, config: Dict, **kwargs) -> Self:
    selector_parser = SelectorConfig.config_parser()
    if selector_parser.has_all_required_args(config):
      return cls(selector=selector_parser.parse(config))

    coordinates_parser = CoordinatesConfig.config_parser()
    if coordinates_parser.has_all_required_args(config):
      return cls(coordinates=coordinates_parser.parse(config))

    ui_selector_parser = UiSelectorConfig.config_parser()
    if ui_selector_parser.has_all_required_args(config):
      return cls(ui_selector=ui_selector_parser.parse(config))

    raise argparse.ArgumentTypeError(
        f"{config} is not a valid coordinate or selector")

  @classmethod
  def from_coordinates(cls, x: int, y: int) -> Self:
    return cls(coordinates=CoordinatesConfig(x, y))

  @classmethod
  def from_selector(cls,
                    selector: str,
                    required: bool = True,
                    scroll_into_view: bool = False,
                    wait: bool = False) -> Self:
    return cls(
        selector=SelectorConfig(
            selector=selector,
            required=required,
            scroll_into_view=scroll_into_view,
            wait=wait))

  @classmethod
  def from_ui_selector(cls, res: str) -> PositionConfig:
    return cls(ui_selector=UiSelectorConfig(res=res))

  @override
  def validate(self) -> None:
    super().validate()
    if (bool(self.coordinates) + bool(self.selector)
        + bool(self.ui_selector)) != 1:
      raise ValueError(
          "Position config must have exactly one coordinates or selector")

  def to_json(self) -> JsonDict:
    if coordinates := self.coordinates:
      return {"x": coordinates.x, "y": coordinates.y}
    if selector := self.selector:
      return {
          "required": selector.required,
          "scroll_into_view": selector.scroll_into_view,
          "selector": selector.selector,
          "wait": selector.wait,
      }
    if ui_selector := self.ui_selector:
      return {"res": ui_selector.res}
    raise ValueError(
        "Position config must have exactly one coordinates or selector")
