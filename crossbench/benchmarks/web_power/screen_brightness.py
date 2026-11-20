# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import dataclasses
import functools
import logging
from typing import TYPE_CHECKING, ClassVar, Final, Self, override

from immutabledict import immutabledict

from crossbench import config, exception
from crossbench.cli.config.device_model_lookup import DeviceModelLookup
from crossbench.config import ConfigError
from crossbench.device_config import RequiredDeviceConfig
from crossbench.parse import NumberParser, ObjectParser

if TYPE_CHECKING:
  from crossbench import path as pth
  from crossbench.plt.base import Platform


@dataclasses.dataclass(frozen=True)
class ScreenBrightnessLookup(DeviceModelLookup[immutabledict[int, int]]):
  """Maps Android device model regexes to {target_nits: screen_brightness}.

  Keys are full-match regular expressions tested against `Platform.model`
  (Android `ro.product.model`), and values map integer luminance targets in
  nits to raw `settings.system.screen_brightness` integers.

  Example:
    {
      "Pixel 9 Pro XL": {"200": 33},
      "SM-S928.*": {"200": 169}
    }
  """

  _MAPPING_REL_PATH: ClassVar[tuple[str, ...]] = (
    "benchmark",
    "web_power",
    "brightness_mapping.hjson",
  )

  @classmethod
  def public_path(cls) -> pth.LocalPath:
    return config.config_dir().joinpath(*cls._MAPPING_REL_PATH)

  @classmethod
  def internal_path(cls) -> pth.LocalPath:
    return config.root_dir().joinpath(
      "internal", "config", *cls._MAPPING_REL_PATH
    )

  @classmethod
  @override
  def _parse_entry_value(
    cls, model_pattern: str, raw_value: object
  ) -> immutabledict[int, int]:
    entry_name = f"brightness mapping for '{model_pattern}'"
    levels: dict[int, int] = {}
    with exception.annotate_argparsing(f"Parsing {entry_name}"):
      raw_levels = ObjectParser.non_empty_dict(raw_value, entry_name)
      for raw_nits, raw_setting in raw_levels.items():
        nits = NumberParser.positive_int(raw_nits, "target nits")
        if nits in levels:
          raise ConfigError(f"Duplicate target nits {nits} in {entry_name}.")
        levels[nits] = NumberParser.positive_zero_int(
          raw_setting, f"brightness setting for {nits} nits"
        )
    return immutabledict(levels)

  @classmethod
  def load_default(cls) -> Self:
    lookup = cls.parse(cls.public_path())
    internal_path = cls.internal_path()
    if internal_path.is_file():
      lookup = lookup.merge(cls.parse(internal_path))
    return lookup


class ScreenBrightnessResolver:
  """Resolves per-device Android screen_brightness device config entries."""

  DEFAULT_TARGET_NITS: ClassVar[int] = 200
  DEFAULT_SCREEN_BRIGHTNESS: ClassVar[int] = 1

  def __init__(self, override_brightness: int | None = None) -> None:
    if override_brightness is not None:
      override_brightness = NumberParser.positive_zero_int(
        override_brightness, "screen_brightness"
      )
    self._override_brightness: Final[int | None] = override_brightness

  @functools.cached_property
  def _lookup(self) -> ScreenBrightnessLookup:
    return ScreenBrightnessLookup.load_default()

  def resolve_brightness(self, platform: Platform) -> int:
    if self._override_brightness is not None:
      return self._override_brightness
    model = platform.model
    if levels := self._lookup.resolve(model):
      if self.DEFAULT_TARGET_NITS in levels:
        return levels[self.DEFAULT_TARGET_NITS]
    logging.warning(
      "No %d-nit screen_brightness mapping for device model '%s'; "
      "falling back to screen_brightness=%d "
      "(pass --screen-brightness to override).",
      self.DEFAULT_TARGET_NITS,
      model,
      self.DEFAULT_SCREEN_BRIGHTNESS,
    )
    return self.DEFAULT_SCREEN_BRIGHTNESS

  def device_config(self, platform: Platform) -> RequiredDeviceConfig | None:
    if not platform.is_android:
      if self._override_brightness is not None:
        raise ConfigError(
          "--screen-brightness is only supported on Android, "
          f"but the active platform is {platform}."
        )
      return None
    brightness = self.resolve_brightness(platform)
    return RequiredDeviceConfig.parse(
      {
        "android": {
          "settings": {
            "system": {
              "screen_brightness": brightness,
            },
          },
        },
      }
    )
