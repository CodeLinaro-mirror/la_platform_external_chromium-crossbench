# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
from typing import Mapping, Self, Sequence, override

from immutabledict import immutabledict
from ordered_set import OrderedSet

from crossbench.config import ConfigObject, ConfigParser
from crossbench.parse import ObjectParser


@dataclasses.dataclass(frozen=True)
class BlinkAIModelConfig(ConfigObject):
  """Configuration for an on-device model variant used by a Blink AI API.

  Defines the model selector name (such as 'default' or 'v4') and any
  Chromium feature flags required to activate that model variant.
  """

  name: str
  features: tuple[str, ...] = ()

  @classmethod
  @override
  def config_parser(cls) -> ConfigParser[Self]:
    """Returns the ConfigParser for BlinkAIModelConfig."""
    parser = ConfigParser(cls)
    parser.add_default_argument(
        "name",
        type=ObjectParser.non_empty_str,
        required=True,
        help="Model selector name (e.g. 'default', 'v4').",
    )
    parser.add_argument(
        "features",
        type=ObjectParser.non_empty_str,
        default=(),
        is_list=True,
        help="Chromium feature flags required to enable this model.",
    )
    return parser

  @classmethod
  @override
  def parse_str(cls, value: str) -> Self:
    """Parses a model selector string into a BlinkAIModelConfig."""
    return cls.config_parser().parse_str(value)

  @override
  def validate(self) -> None:
    """Validates that the model name and feature flags are non-empty strings."""
    ObjectParser.non_empty_str(self.name, "name")
    for feature in self.features:
      ObjectParser.non_empty_str(feature, "features")


@dataclasses.dataclass(frozen=True)
class BlinkAISubstoryConfig(ConfigObject):
  """Configuration for an individual substory within a Blink AI API.

  Specifies the substory name, optional per-substory Chromium feature flags,
  and an optional default model selector override.
  """

  name: str
  features: tuple[str, ...] = ()
  model: str | None = None

  @classmethod
  @override
  def config_parser(cls) -> ConfigParser[Self]:
    """Returns the ConfigParser for BlinkAISubstoryConfig."""
    parser = ConfigParser(cls)
    parser.add_default_argument(
        "name",
        type=ObjectParser.non_empty_str,
        required=True,
        help="Substory identifier (e.g. 'language_model', 'mtp_summary').",
    )
    parser.add_argument(
        "features",
        type=ObjectParser.non_empty_str,
        default=(),
        is_list=True,
        help="Additional Chromium feature flags required by this substory.",
    )
    parser.add_argument(
        "model",
        type=ObjectParser.non_empty_str,
        default=None,
        help="Optional model selector override for this substory.",
    )
    return parser

  @classmethod
  @override
  def parse_str(cls, value: str) -> Self:
    """Parses a substory name string into a BlinkAISubstoryConfig."""
    return cls.config_parser().parse_str(value)

  @override
  def validate(self) -> None:
    """Validates that the substory name, feature flags, and model are valid."""
    ObjectParser.non_empty_str(self.name, "name")
    for feature in self.features:
      ObjectParser.non_empty_str(feature, "features")
    if self.model is not None:
      ObjectParser.non_empty_str(self.model, "model")


@dataclasses.dataclass(frozen=True)
class BlinkAIApiConfig(ConfigObject):
  """Configuration for a Chrome Built-in AI API benchmark target.

  Describes the API's short identifier, JavaScript global object name,
  base Chromium feature flags, supported model variants, and substories.
  """

  name: str
  js_global: str
  base_features: tuple[str, ...] = ()
  default_model: str = "default"
  default_substories: tuple[str, ...] = ()
  models: immutabledict[str, BlinkAIModelConfig] = dataclasses.field(
      default_factory=immutabledict)
  substories: immutabledict[str, BlinkAISubstoryConfig] = dataclasses.field(
      default_factory=immutabledict)

  @classmethod
  def _normalize_models(
      cls,
      models: Sequence[BlinkAIModelConfig]
      | Mapping[str, BlinkAIModelConfig] = (),
  ) -> immutabledict[str, BlinkAIModelConfig]:
    if isinstance(models, Mapping):
      return immutabledict(models)
    model_map: dict[str, BlinkAIModelConfig] = {}
    for model_cfg in models:
      if model_cfg.name in model_map:
        raise ValueError(f"Duplicate model config name: {model_cfg.name!r}")
      model_map[model_cfg.name] = model_cfg
    return immutabledict(model_map)

  @classmethod
  def _normalize_substories(
      cls,
      substories: Sequence[BlinkAISubstoryConfig]
      | Mapping[str, BlinkAISubstoryConfig] = (),
  ) -> immutabledict[str, BlinkAISubstoryConfig]:
    if isinstance(substories, Mapping):
      return immutabledict(substories)
    substory_map: dict[str, BlinkAISubstoryConfig] = {}
    for substory_cfg in substories:
      if substory_cfg.name in substory_map:
        raise ValueError(
            f"Duplicate substory config name: {substory_cfg.name!r}")
      substory_map[substory_cfg.name] = substory_cfg
    return immutabledict(substory_map)

  @classmethod
  @override
  def create(
      cls,
      name: str,
      js_global: str,
      base_features: Sequence[str] = (),
      default_model: str = "default",
      default_substories: Sequence[str] = (),
      models: Sequence[BlinkAIModelConfig]
      | Mapping[str, BlinkAIModelConfig] = (),
      substories: Sequence[BlinkAISubstoryConfig]
      | Mapping[str, BlinkAISubstoryConfig] = (),
  ) -> Self:
    return cls(
        name=name,
        js_global=js_global,
        base_features=tuple(base_features),
        default_model=default_model,
        default_substories=tuple(default_substories),
        models=cls._normalize_models(models),
        substories=cls._normalize_substories(substories),
    )

  @classmethod
  @override
  def config_parser(cls) -> ConfigParser[Self]:
    """Returns the ConfigParser for BlinkAIApiConfig."""
    parser = ConfigParser(cls)
    parser.add_argument(
        "name",
        type=ObjectParser.non_empty_str,
        required=True,
        help="Short identifier for the Built-in AI API.",
    )
    parser.add_argument(
        "js_global",
        type=ObjectParser.non_empty_str,
        required=True,
        help="Global window property exposed by the API in JavaScript.",
    )
    parser.add_argument(
        "base_features",
        type=ObjectParser.non_empty_str,
        default=(),
        is_list=True,
        help="Base Chromium feature flags always enabled for this API.",
    )
    parser.add_argument(
        "default_model",
        type=ObjectParser.non_empty_str,
        default="default",
        help="Default model selector name for this API.",
    )
    parser.add_argument(
        "default_substories",
        type=ObjectParser.non_empty_str,
        default=(),
        is_list=True,
        help="Substory names executed when --stories=default.",
    )
    parser.add_argument(
        "models",
        type=BlinkAIModelConfig,
        default=(),
        is_list=True,
        help="Supported BlinkAIModelConfig variants for this API.",
    )
    parser.add_argument(
        "substories",
        type=BlinkAISubstoryConfig,
        default=(),
        is_list=True,
        help="Supported BlinkAISubstoryConfig entries for this API.",
    )
    return parser

  @classmethod
  @override
  def parse_str(cls, value: str) -> Self:
    """Parses '<name>:<js_global>' shorthand into a BlinkAIApiConfig."""
    value = ObjectParser.non_empty_str(value, "api_config")
    if ":" not in value:
      raise ValueError(f"Expected '<name>:<js_global>' for {cls.__name__}, "
                       f"but got {value!r}.")
    name, js_global = value.split(":", maxsplit=1)
    return cls.create(
        name=ObjectParser.non_empty_str(name, "name"),
        js_global=ObjectParser.non_empty_str(js_global, "js_global"),
    )

  @override
  def validate(self) -> None:
    """Validates API name, JavaScript global symbol, and nested mappings."""
    ObjectParser.non_empty_str(self.name, "name")
    ObjectParser.non_empty_str(self.js_global, "js_global")
    if not self.js_global.isidentifier():
      raise ValueError(
          f"Invalid JavaScript global identifier {self.js_global!r} for API "
          f"{self.name!r}.")
    ObjectParser.non_empty_str(self.default_model, "default_model")
    for feature in self.base_features:
      ObjectParser.non_empty_str(feature, "base_features")
    for substory in self.default_substories:
      ObjectParser.non_empty_str(substory, "default_substories")
    for model_name, model_cfg in self.models.items():
      ObjectParser.non_empty_str(model_name, "model name")
      if model_cfg.name != model_name:
        raise ValueError(
            f"Model key {model_name!r} does not match model config name "
            f"{model_cfg.name!r}.")
    if self.models:
      self.get_model_config(self.default_model)
    for substory_name, substory_cfg in self.substories.items():
      ObjectParser.non_empty_str(substory_name, "substory name")
      if substory_cfg.name != substory_name:
        raise ValueError(
            f"Substory key {substory_name!r} does not match substory config "
            f"name {substory_cfg.name!r}.")
      if self.models and substory_cfg.model is not None:
        self.get_model_config(substory_cfg.model)
    if self.substories:
      for substory in self.default_substories:
        self.get_substory_config(substory)

  @property
  def all_substory_names(self) -> tuple[str, ...]:
    """Returns all substory names registered for this API."""
    return tuple(self.substories)

  def get_model_config(self, model_name: str) -> BlinkAIModelConfig:
    """Returns the model configuration for the given model selector name."""
    if cfg := self.models.get(model_name):
      return cfg
    available = ", ".join(self.models)
    raise ValueError(f"Unknown model {model_name!r} for API {self.name!r}. "
                     f"Available models: {available}")

  def get_substory_config(self, substory_name: str) -> BlinkAISubstoryConfig:
    """Returns the substory configuration for the given substory name."""
    if cfg := self.substories.get(substory_name):
      return cfg
    available = ", ".join(self.substories)
    raise ValueError(
        f"Unknown substory {substory_name!r} for API {self.name!r}. "
        f"Available substories: {available}")

  def resolve_model_name(self,
                         substory_name: str,
                         model: str | None = None) -> str:
    """Resolves the effective model name for a substory and model override."""
    substory_cfg = self.get_substory_config(substory_name)
    if model is not None:
      if substory_cfg.model is not None and model != substory_cfg.model:
        raise ValueError(f"Substory {substory_name!r} requires model "
                         f"{substory_cfg.model!r}, which conflicts with "
                         f"--model={model!r}.")
      resolved_model = model
    elif substory_cfg.model is not None:
      resolved_model = substory_cfg.model
    else:
      resolved_model = self.default_model
    self.get_model_config(resolved_model)
    return resolved_model

  def resolve_features(self,
                       substories: Sequence[str] = (),
                       model: str | None = None) -> tuple[str, ...]:
    """Resolves the deduplicated Chromium feature flags for a story run."""
    features: OrderedSet[str] = OrderedSet(self.base_features)
    if not substories:
      resolved_model = self.default_model if model is None else model
      features.update(self.get_model_config(resolved_model).features)
      return tuple(features)
    for substory_name in substories:
      substory_cfg = self.get_substory_config(substory_name)
      features.update(substory_cfg.features)
      resolved_model = self.resolve_model_name(substory_name, model)
      features.update(self.get_model_config(resolved_model).features)
    return tuple(features)

  def validate_combined_substories(self,
                                   substories: Sequence[str],
                                   model: str | None = None) -> None:
    """Validates that combined substories share a compatible model and flags."""
    if len(substories) <= 1:
      return
    first_substory = substories[0]
    expected_model = self.resolve_model_name(first_substory, model)
    expected_features = set(
        self.resolve_features((first_substory,), model=model))
    for substory in substories[1:]:
      substory_model = self.resolve_model_name(substory, model)
      substory_features = set(self.resolve_features((substory,), model=model))
      if (substory_model != expected_model or
          substory_features != expected_features):
        raise ValueError(
            f"Cannot combine substories {first_substory!r} and {substory!r} "
            "with conflicting model or feature configurations in --combined "
            "mode. Pass --separate to run them in separate browser sessions.")
