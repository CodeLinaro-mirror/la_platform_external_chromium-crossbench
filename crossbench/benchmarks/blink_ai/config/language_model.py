# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import Final

from .base import BlinkAIApiConfig, BlinkAIModelConfig, BlinkAISubstoryConfig

_MTP_FEATURES: Final[tuple[str, ...]] = ("OnDeviceModelSpeculativeDecoding",)

LANGUAGE_MODEL_API: Final[BlinkAIApiConfig] = BlinkAIApiConfig.create(
    name="language_model",
    js_global="LanguageModel",
    base_features=(
        ("OnDeviceModelPerformanceParams:"
         "compatible_on_device_performance_classes/*"),
        "OnDeviceModelIdleTimeout:on_device_model_idle_timeout/10s",
        "OnDeviceAiDefaultEnabled",
    ),
    default_model="default",
    default_substories=(
        "language_model",
        "multimodal_image",
        "multimodal_images",
        "multimodal_audio",
    ),
    models=(
        BlinkAIModelConfig("default"),
        BlinkAIModelConfig(
            "v4",
            features=(
                "OnDeviceModelConversationBackend",
                "AIApiFoundationalModel:model_version/v4",
            ),
        ),
    ),
    substories=(
        BlinkAISubstoryConfig("language_model"),
        BlinkAISubstoryConfig("multimodal_image"),
        BlinkAISubstoryConfig("multimodal_images"),
        BlinkAISubstoryConfig("multimodal_audio"),
        BlinkAISubstoryConfig("mtp_summary", features=_MTP_FEATURES),
        BlinkAISubstoryConfig("mtp_flight", features=_MTP_FEATURES),
        BlinkAISubstoryConfig("mtp_emoji", features=_MTP_FEATURES),
        # Article summary with constrained decoding (responseConstraint).
        BlinkAISubstoryConfig(
            "mtp_constrained_summary", features=_MTP_FEATURES),
        BlinkAISubstoryConfig(
            "tool_calling",
            features=("AIPromptAPIToolUse",),
            model="v4",
        ),
    ),
)
