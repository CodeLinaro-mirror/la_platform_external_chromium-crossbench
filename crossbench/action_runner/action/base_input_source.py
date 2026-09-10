# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import dataclasses
import functools
from typing import TYPE_CHECKING, Self

from typing_extensions import override

from crossbench.action_runner.action.base_duration import BaseDurationAction
from crossbench.benchmarks.loading.input_source import InputSource
from crossbench.parse import ObjectParser

if TYPE_CHECKING:
  from crossbench.config import ConfigParser
  from crossbench.types import JsonDict


@dataclasses.dataclass(frozen=True, eq=False)
class InputSourceAction(BaseDurationAction, metaclass=abc.ABCMeta):
  source: InputSource = InputSource.JS
  source_device: str | None = dataclasses.field(default=None, kw_only=True)

  @classmethod
  @override
  @functools.cache
  def config_parser(cls: type[Self]) -> ConfigParser[Self]:
    parser = super().config_parser()
    parser.add_argument(
        "source", type=InputSource.parse, default=InputSource.JS)
    parser.add_argument(
        "source_device",
        type=ObjectParser.non_empty_str,
        required=False,
        default=None)
    return parser

  @property
  def input_source(self) -> InputSource:
    return self.source

  @override
  def validate(self) -> None:
    super().validate()
    self.validate_input_source()

  def validate_input_source(self) -> None:
    if self.input_source not in self.supported_input_sources():
      raise ValueError(
          f"Unsupported input source for {self.__class__.__name__}")

  @abc.abstractmethod
  def supported_input_sources(self) -> tuple[InputSource, ...]:
    pass

  @override
  def to_json(self) -> JsonDict:
    details = super().to_json()
    details["source"] = self.input_source
    if self.source_device:
      details["source_device"] = self.source_device
    return details
