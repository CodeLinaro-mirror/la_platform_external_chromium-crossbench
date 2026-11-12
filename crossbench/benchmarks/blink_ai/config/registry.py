# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from immutabledict import immutabledict

from crossbench.helper.collection_helper import close_matches_message

from .language_model import LANGUAGE_MODEL_API

if TYPE_CHECKING:
  from .base import BlinkAIApiConfig

API_CONFIGS: Final[immutabledict[str, BlinkAIApiConfig]] = immutabledict(
  {
    LANGUAGE_MODEL_API.name: LANGUAGE_MODEL_API,
  }
)


class BlinkAIApiRegistry:
  """Registry of supported Blink AI API benchmark configurations."""

  @classmethod
  def get(cls, api_name: str) -> BlinkAIApiConfig:
    """Returns the registered BlinkAIApiConfig for the given API name."""
    if cfg := API_CONFIGS.get(api_name):
      return cfg
    message, _ = close_matches_message(
      api_name, API_CONFIGS.keys(), "Blink AI API"
    )
    raise ValueError(message)


get_api_config = BlinkAIApiRegistry.get
