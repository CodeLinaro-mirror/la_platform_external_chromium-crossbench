# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime as dt
from typing import Final

from .base import BlinkAIApiConfig, BlinkAISubstoryConfig
from .language_model import LANGUAGE_MODEL_API

LANGUAGE_MODEL_QUALITY_API: Final[BlinkAIApiConfig] = BlinkAIApiConfig.create(
  name="language_model_quality",
  js_global="LanguageModel",
  base_features=(
    (
      "OnDeviceModelPerformanceParams:"
      "compatible_on_device_performance_classes/*"
    ),
    "OnDeviceAiDefaultEnabled",
    "AIPromptAPIParams",
  ),
  default_model=LANGUAGE_MODEL_API.default_model,
  default_substories=(
    "mmlu",
    "vizwiz",
    "librispeech",
  ),
  models=LANGUAGE_MODEL_API.models,
  substories=(
    BlinkAISubstoryConfig("mmlu"),
    BlinkAISubstoryConfig("vizwiz"),
    BlinkAISubstoryConfig("librispeech"),
  ),
  substory_duration=dt.timedelta(minutes=5),
)
