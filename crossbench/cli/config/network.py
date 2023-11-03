# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations
import argparse

import dataclasses
from typing import Any, Dict

from frozendict import frozendict

from crossbench import compat
from crossbench.config import ConfigObject, ConfigParser


class NetworkType(compat.StrEnumWithHelp):
  LIVE = ("live", "Live network.")
  REPLAY = ("replay", "Replayed network from a wpr.go archive.")
  LOCAL = ("local", "Serve content from a local http file server.")


@dataclasses.dataclass(frozen=True)
class TrafficConfig(ConfigObject):

  @classmethod
  def default(cls) -> TrafficConfig:
    return TrafficConfig()

  @classmethod
  def loads(cls, value: str) -> TrafficConfig:
    # TODO: implement
    if not value:
      raise argparse.ArgumentTypeError("Cannot parse empty string")
    return cls.default()

  @classmethod
  def load_dict(cls, config: Dict[str, Any]) -> TrafficConfig:
    # TODO: implement
    # return cls.config_parser().parse(config)
    return cls.default()


@dataclasses.dataclass(frozen=True)
class NetworkConfig(ConfigObject):
  type: NetworkType = NetworkType.LIVE
  traffic: TrafficConfig = TrafficConfig.default()
  settings: Dict[str, str] = {}

  @classmethod
  def default(cls) -> NetworkConfig:
    return NetworkConfig()

  @classmethod
  def config_parser(cls) -> ConfigParser[NetworkConfig]:
    parser = ConfigParser("DriverConfig parser", cls)
    parser.add_argument("type", type=NetworkType, default=NetworkType.LIVE)
    parser.add_argument("traffic", type=TrafficConfig)
    parser.add_argument("settings", type=frozendict)
    return parser

  @classmethod
  def loads(cls, value: str) -> NetworkConfig:
    # TODO: implement
    if not value:
      raise argparse.ArgumentTypeError("Cannot parse empty string")
    return cls.default()

  @classmethod
  def load_dict(cls, config: Dict[str, Any]) -> NetworkConfig:
    # TODO: implement
    # return cls.config_parser().parse(config)
    return cls.default()
