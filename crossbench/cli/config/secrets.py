# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
from typing import Dict, Optional

from crossbench.config import ConfigObject, ConfigParser
from crossbench.parse import ObjectParser

@dataclasses.dataclass(frozen=True)
class Secrets(ConfigObject):
  google: Optional[UsernamePassword] = None

  @classmethod
  def config_parser(cls) -> ConfigParser[Secrets]:
    parser = ConfigParser(cls)
    parser.add_argument("google", type=GoogleUsernamePassword)
    return parser

  @classmethod
  def parse_str(cls, value: str) -> Secrets:
    if value[0] == "{":
      return cls.parse_inline_hjson(value)
    raise NotImplementedError("Cannot create secrets from string")

  @classmethod
  def parse_dict(cls, config: Dict) -> Secrets:
    return cls.config_parser().parse(config)

  def merge(self, fallback: Secrets) -> Secrets:
    return Secrets(self.google or fallback.google)

@dataclasses.dataclass(frozen=True)
class UsernamePassword(ConfigObject):
  username: str
  password: str

  @classmethod
  def config_parser(cls) -> ConfigParser[UsernamePassword]:
    parser = ConfigParser(cls)
    parser.add_argument(
        "username",
        aliases=("user", "usr", "account"),
        type=ObjectParser.non_empty_str,
        required=True)
    parser.add_argument(
        "password",
        aliases=("pass", "pw"),
        type=ObjectParser.any_str,
        required=True)
    return parser

  @classmethod
  def parse_dict(cls, config: Dict) -> UsernamePassword:
    return cls.config_parser().parse(config)

  @classmethod
  def parse_str(cls, value: str):
    # TODO: maybe support passwd style string format
    raise NotImplementedError("Cannot support")


class GoogleUsernamePassword(UsernamePassword):
  pass
