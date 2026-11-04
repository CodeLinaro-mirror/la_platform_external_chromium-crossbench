# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import unittest

from immutabledict import immutabledict

from crossbench.benchmarks.blink_ai.config.base import BlinkAIApiConfig, \
    BlinkAIModelConfig, BlinkAISubstoryConfig
from crossbench.benchmarks.blink_ai.config.language_model import \
    LANGUAGE_MODEL_API
from crossbench.benchmarks.blink_ai.config.registry import API_CONFIGS, \
    BlinkAIApiRegistry, get_api_config
from tests import test_helper


class BlinkAIConfigTestCase(unittest.TestCase):

  def test_model_config_parse(self) -> None:
    short_cfg = BlinkAIModelConfig.parse("v4")
    self.assertEqual(short_cfg, BlinkAIModelConfig(name="v4"))
    self.assertEqual(BlinkAIModelConfig.parse_str("v4"), short_cfg)

    dict_cfg = BlinkAIModelConfig.parse({
        "name": "v4",
        "features": ["OnDeviceModelConversationBackend", "Foo"],
    })
    self.assertEqual(
        dict_cfg,
        BlinkAIModelConfig(
            name="v4",
            features=("OnDeviceModelConversationBackend", "Foo"),
        ),
    )

    hjson_cfg = BlinkAIModelConfig.parse("{name: 'v4', features: ['Foo']}")
    self.assertEqual(hjson_cfg,
                     BlinkAIModelConfig(name="v4", features=("Foo",)))

    with self.assertRaises(argparse.ArgumentTypeError):
      BlinkAIModelConfig.parse("")
    with self.assertRaises(argparse.ArgumentTypeError):
      BlinkAIModelConfig.parse({})

  def test_substory_config_parse(self) -> None:
    short_cfg = BlinkAISubstoryConfig.parse("writer_short")
    self.assertEqual(short_cfg, BlinkAISubstoryConfig(name="writer_short"))
    self.assertEqual(BlinkAISubstoryConfig.parse_str("writer_short"), short_cfg)

    dict_cfg = BlinkAISubstoryConfig.parse({
        "name": "writer_long",
        "features": ["FeatureA"],
        "model": "v4",
    })
    self.assertEqual(
        dict_cfg,
        BlinkAISubstoryConfig(
            name="writer_long",
            features=("FeatureA",),
            model="v4",
        ),
    )

    hjson_cfg = BlinkAISubstoryConfig.parse(
        "{name: 'writer_long', features: ['FeatureA'], model: 'v4'}")
    self.assertEqual(hjson_cfg, dict_cfg)

    with self.assertRaises(argparse.ArgumentTypeError):
      BlinkAISubstoryConfig.parse("")
    with self.assertRaises(argparse.ArgumentTypeError):
      BlinkAISubstoryConfig.parse({})

  def test_api_config_parse(self) -> None:
    short_cfg = BlinkAIApiConfig.parse("language_model:LanguageModel")
    self.assertEqual(
        short_cfg,
        BlinkAIApiConfig.create(
            name="language_model", js_global="LanguageModel"),
    )
    self.assertEqual(
        BlinkAIApiConfig.parse_str("language_model:LanguageModel"),
        short_cfg,
    )
    self.assertIsInstance(hash(short_cfg), int)

    dict_cfg = BlinkAIApiConfig.parse({
        "name":
            "writer",
        "js_global":
            "Writer",
        "base_features": ["AIWriterAPI"],
        "default_model":
            "v1",
        "default_substories": ["writer_short"],
        "models": [{
            "name": "v1",
            "features": ["WriterModelV1"],
        }],
        "substories": [
            "writer_short",
            {
                "name": "writer_long",
                "features": ["FeatureB"],
                "model": "v1",
            },
        ],
    })
    self.assertEqual(dict_cfg.name, "writer")
    self.assertEqual(dict_cfg.js_global, "Writer")
    self.assertEqual(dict_cfg.base_features, ("AIWriterAPI",))
    self.assertEqual(dict_cfg.default_model, "v1")
    self.assertEqual(dict_cfg.default_substories, ("writer_short",))
    self.assertIsInstance(dict_cfg.models, immutabledict)
    self.assertIsInstance(dict_cfg.substories, immutabledict)
    self.assertIsInstance(hash(dict_cfg), int)
    self.assertEqual(
        dict_cfg.get_model_config("v1"),
        BlinkAIModelConfig(name="v1", features=("WriterModelV1",)),
    )
    self.assertEqual(
        dict_cfg.get_substory_config("writer_short"),
        BlinkAISubstoryConfig(name="writer_short"),
    )
    self.assertEqual(
        dict_cfg.get_substory_config("writer_long"),
        BlinkAISubstoryConfig(
            name="writer_long",
            features=("FeatureB",),
            model="v1",
        ),
    )

    with self.assertRaises(argparse.ArgumentTypeError):
      BlinkAIApiConfig.parse("missing_colon")
    with self.assertRaises(argparse.ArgumentTypeError):
      BlinkAIApiConfig.parse({
          "name": "writer",
          "js_global": "Writer",
          "models": ["v1", "v1"],
      })
    with self.assertRaises(argparse.ArgumentTypeError):
      BlinkAIApiConfig.parse({
          "name": "writer",
          "js_global": "Writer",
          "substories": ["short", "short"],
      })
    with self.assertRaises(ValueError):
      BlinkAIApiConfig.create(
          name="writer",
          js_global="Writer",
          models=immutabledict({"v1": BlinkAIModelConfig("mismatch")}),
      )
    with self.assertRaises(ValueError):
      BlinkAIApiConfig.create(
          name="writer",
          js_global="Writer",
          substories=immutabledict({
              "writer_short": BlinkAISubstoryConfig("mismatch"),
          }),
      )
    with self.assertRaises(ValueError):
      BlinkAIApiConfig.create(
          name="writer",
          js_global="window.Writer",
      )
    with self.assertRaises(ValueError):
      BlinkAIApiConfig.create(
          name="writer",
          js_global="Writer",
          default_model="unknown_model",
          models=(BlinkAIModelConfig("v1"),),
      )
    with self.assertRaises(ValueError):
      BlinkAIApiConfig.create(
          name="writer",
          js_global="Writer",
          default_model="v1",
          models=(BlinkAIModelConfig("v1"),),
          substories=(BlinkAISubstoryConfig(
              "writer_short", model="unknown_model"),),
      )
    with self.assertRaises(ValueError):
      BlinkAIApiConfig.create(
          name="writer",
          js_global="Writer",
          default_substories=("unknown_substory",),
          substories=(BlinkAISubstoryConfig("writer_short"),),
      )

  def test_language_model_api_config_resolution(self) -> None:
    self.assertIn("language_model", API_CONFIGS)
    api_cfg = get_api_config("language_model")
    self.assertEqual(api_cfg, LANGUAGE_MODEL_API)
    self.assertEqual(
        BlinkAIApiRegistry.get("language_model"), LANGUAGE_MODEL_API)
    self.assertEqual(api_cfg.js_global, "LanguageModel")
    self.assertEqual(
        LANGUAGE_MODEL_API.base_features,
        (
            ("OnDeviceModelPerformanceParams:"
             "compatible_on_device_performance_classes/*"),
            "OnDeviceModelIdleTimeout:on_device_model_idle_timeout/10s",
            "OnDeviceAiDefaultEnabled",
        ),
    )

    with self.assertRaises(ValueError) as cm_err:
      get_api_config("language_modl")
    self.assertIn("language_model", str(cm_err.exception))
    with self.assertRaises(ValueError):
      api_cfg.get_model_config("unknown_model")
    with self.assertRaises(ValueError):
      api_cfg.get_substory_config("unknown_substory")
    with self.assertRaises(ValueError):
      api_cfg.resolve_model_name("language_model", model="")
    with self.assertRaises(ValueError):
      api_cfg.resolve_features(("language_model",), model="")
    with self.assertRaises(ValueError):
      api_cfg.resolve_model_name("tool_calling", model="default")
    self.assertEqual(
        api_cfg.resolve_model_name("tool_calling", model="v4"), "v4")

    self.assertEqual(
        api_cfg.resolve_features(()),
        LANGUAGE_MODEL_API.base_features,
    )
    self.assertEqual(
        api_cfg.resolve_features(("language_model",)),
        LANGUAGE_MODEL_API.base_features,
    )
    self.assertEqual(
        api_cfg.resolve_features(("mtp_summary",)),
        LANGUAGE_MODEL_API.base_features +
        ("OnDeviceModelSpeculativeDecoding",),
    )
    self.assertEqual(
        api_cfg.resolve_features(("tool_calling",)),
        LANGUAGE_MODEL_API.base_features + (
            "AIPromptAPIToolUse",
            "OnDeviceModelConversationBackend",
            "AIApiFoundationalModel:model_version/v4",
        ),
    )
    self.assertEqual(
        api_cfg.resolve_features(("language_model",), model="v4"),
        LANGUAGE_MODEL_API.base_features + (
            "OnDeviceModelConversationBackend",
            "AIApiFoundationalModel:model_version/v4",
        ),
    )

    api_cfg.validate_combined_substories(("mtp_summary", "mtp_flight"))
    with self.assertRaises(ValueError):
      api_cfg.validate_combined_substories(("language_model", "mtp_summary"))
    with self.assertRaises(ValueError):
      api_cfg.validate_combined_substories(("language_model", "tool_calling"))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
