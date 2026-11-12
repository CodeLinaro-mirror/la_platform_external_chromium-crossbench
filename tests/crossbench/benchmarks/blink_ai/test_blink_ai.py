# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import threading
from typing import TYPE_CHECKING, Any, Final, override
from unittest import mock

from immutabledict import immutabledict

from crossbench.benchmarks.blink_ai.blink_ai import (
  BlinkAIBenchmark,
  BlinkAIStory,
  BlinkAIStoryFilter,
)
from crossbench.benchmarks.blink_ai.config.base import (
  BlinkAIApiConfig,
  BlinkAIModelConfig,
  BlinkAISubstoryConfig,
)
from crossbench.benchmarks.blink_ai.config.language_model import (
  LANGUAGE_MODEL_API,
)
from crossbench.benchmarks.blink_ai.config.registry import API_CONFIGS
from crossbench.benchmarks.blink_ai.probe import (
  BYTES_PER_MB,
  MIN_VRAM_INTERVAL,
  BlinkAIProbe,
  BlinkAIProbeContext,
)
from crossbench.env.runner_env import EnvConfig, ValidationMode
from crossbench.runner.runner import Runner
from crossbench.stories.press_benchmark import MAX_STORY_NAME_LEN
from tests import test_helper
from tests.crossbench.benchmarks import helper

if TYPE_CHECKING:
  from tests.crossbench.mock_browser import MockBrowser

SAMPLE_STORY_METRICS: Final[immutabledict[str, Any]] = immutabledict(
  {
    "sessionCreationTimeMs": 120.5,
    "coldTimeToFirstTokenMs": 45.2,
    "coldTotalPromptTimeMs": 250.0,
    "coldChunksPerSecond": 45.8,
    "warmTimeToFirstTokenMs": [12.5, 10.2, 9.8],
    "warmTotalPromptTimeMs": [110.0, 95.0, 92.0],
    "warmChunksPerSecond": [50.2, 55.1, 56.3],
  }
)
VRAM_STAT_NAMES: Final[tuple[str, ...]] = ("peak", "baseline", "delta")


class BlinkAITestCase(helper.SubStoryTestCase):
  @override
  def setUp(self) -> None:
    super().setUp()
    self.platform.gpu_vram_used = mock.Mock(return_value={})

  @property
  @override
  def benchmark_cls(self):
    return BlinkAIBenchmark

  @property
  @override
  def story_cls(self):
    return BlinkAIStory

  @property
  def probe_cls(self):
    return BlinkAIProbe

  @property
  def probe_context_cls(self):
    return BlinkAIProbeContext

  @override
  def test_instantiate_all_stories(self) -> None:
    with self.assertRaises(ValueError):
      self.story_filter(self.story_cls.all_story_names(), separate=False)
    stories = self.story_filter(
      self.story_cls.all_story_names(), separate=True
    ).stories
    self.benchmark_cls(stories)

  def _setup_run_js_expect(
    self,
    browser: MockBrowser,
    probe_results: dict[str, Any],
    status: str = "success",
  ) -> None:
    # wait_js_condition for window.LanguageModel
    browser.expect_js(result=True)
    # JS click for #start-button
    browser.expect_js(result=None)
    # wait_js_condition for window.testStatus !== 'running'
    browser.expect_js(result=True)
    # window.testStatus check
    browser.expect_js(result=status)
    if status == "success":
      # window.metrics check in story run()
      browser.expect_js(result=probe_results)
    # window.metrics in probe (JsonResultProbeContext)
    browser.expect_js(result=json.dumps(probe_results))

  def _run_vram_probe_context(
    self,
    samples: list[dict[str, float]],
    js_metrics: dict[str, Any],
  ) -> dict[str, Any]:
    all_sampled = threading.Event()
    call_count = 0

    def side_effect() -> dict[str, float]:
      nonlocal call_count
      result = samples[min(call_count, len(samples) - 1)]
      call_count += 1
      if call_count >= len(samples):
        all_sampled.set()
      return result

    probe = BlinkAIProbe(vram_interval=MIN_VRAM_INTERVAL)

    mock_browser = mock.Mock()
    mock_browser.platform = self.platform
    mock_browser.host_platform = self.platform

    mock_run = mock.Mock()
    mock_run.browser = mock_browser
    mock_run.get_default_probe_result_path = mock.Mock(
      return_value=self.out_dir / "blink_ai.json"
    )
    mock_run.results = mock.Mock()

    mock_actions = mock.MagicMock()
    mock_actions.__enter__.return_value = mock_actions
    mock_actions.js.return_value = json.dumps(js_metrics)
    mock_run.actions = mock.MagicMock(return_value=mock_actions)

    context = BlinkAIProbeContext(probe, mock_run)
    with mock.patch.object(
      self.platform, "gpu_vram_used", side_effect=side_effect
    ):
      context.setup()
      context.start()
      self.assertTrue(all_sampled.wait(timeout=5.0))
      context.stop()

    data = context.to_json(mock_actions)
    assert isinstance(data, dict)
    return data

  def _assert_vram_stats(
    self,
    data: dict[str, Any],
    peak_mb: float,
    baseline_mb: float,
    gpu_id: str | None = None,
    check_flat_gpu: bool = False,
  ) -> None:
    expected = {
      "peak": peak_mb,
      "baseline": baseline_mb,
      "delta": peak_mb - baseline_mb,
    }
    if gpu_id is None:
      for stat, val_mb in expected.items():
        self.assertEqual(data["vram"][f"{stat}_mb"], val_mb)
        self.assertEqual(data[f"vram_{stat}_mb"], val_mb)
        self.assertEqual(
          data[f"vram_{stat}_bytes"], round(val_mb * BYTES_PER_MB)
        )
      return

    self.assertDictEqual(
      data["vram"][gpu_id],
      {f"{stat}_mb": val_mb for stat, val_mb in expected.items()},
    )
    if check_flat_gpu:
      for stat, val_mb in expected.items():
        self.assertEqual(data[f"vram_{gpu_id}_{stat}_mb"], val_mb)
        self.assertEqual(
          data[f"vram_{gpu_id}_{stat}_bytes"], round(val_mb * BYTES_PER_MB)
        )

  def test_run_default(self):
    stories = self.story_cls.default()
    benchmark = self.benchmark_cls(stories)
    self.assertTrue(len(benchmark.describe()) > 0)

    probe_results: dict[str, Any] = {
      "downloadTimeMs": 500.5,
      **SAMPLE_STORY_METRICS,
    }
    for substory in self.story_cls.default_story_names():
      probe_results[substory] = dict(SAMPLE_STORY_METRICS)

    repetitions = 2
    for _ in range(repetitions):
      for browser in self.browsers:
        self._setup_run_js_expect(browser, probe_results)

    for browser in self.browsers:
      browser.expected_js = copy.deepcopy(browser.expected_js)

    runner = Runner(
      self.out_dir,
      self.browsers,
      benchmark,
      env_config=EnvConfig(),
      env_validation_mode=ValidationMode.SKIP,
      platform=self.platform,
      repetitions=repetitions,
      throw=True,
      in_memory_result_db=True,
    )

    with mock.patch.object(self.benchmark_cls, "validate_url") as cm:
      runner.run()
    cm.assert_called_once()

    expected_query = (
      "?api=language_model&stories=language_model"
      "%2Cmultimodal_image%2Cmultimodal_images"
      "%2Cmultimodal_audio"
    )
    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertEqual(len(urls), repetitions)
      self.assertIn(self.story_cls.URL + expected_query, urls)
      self.assertSequenceEqual(browser.expected_js, [])

  def test_run_single_story(self):
    stories = self.story_cls.from_names(["language_model"])
    benchmark = self.benchmark_cls(stories)
    self.assertTrue(len(benchmark.describe()) > 0)

    probe_results = {"downloadTimeMs": 500.5, **SAMPLE_STORY_METRICS}

    repetitions = 1
    for _ in range(repetitions):
      for browser in self.browsers:
        self._setup_run_js_expect(browser, probe_results)

    for browser in self.browsers:
      browser.expected_js = copy.deepcopy(browser.expected_js)

    runner = Runner(
      self.out_dir,
      self.browsers,
      benchmark,
      env_config=EnvConfig(),
      env_validation_mode=ValidationMode.SKIP,
      platform=self.platform,
      repetitions=repetitions,
      throw=True,
      in_memory_result_db=True,
    )

    with mock.patch.object(self.benchmark_cls, "validate_url") as cm:
      runner.run()
    cm.assert_called_once()

    for browser in self.browsers:
      urls = self.filter_splashscreen_urls(browser.url_list)
      self.assertEqual(len(urls), repetitions)
      self.assertIn(
        self.story_cls.URL + "?api=language_model&stories=language_model", urls
      )
      self.assertSequenceEqual(browser.expected_js, [])

  def test_custom_url(self):
    custom_url = "http://test.example.com/blink_ai"
    stories = self.story_cls.from_names(["language_model"], url=custom_url)
    self.assertEqual(len(stories), 1)
    story = stories[0]
    self.assertDictEqual(
      story.url_params,
      {
        "api": "language_model",
        "stories": "language_model",
      },
    )
    self.assertEqual(
      story.test_url, custom_url + "?api=language_model&stories=language_model"
    )

  def test_run_error(self):
    stories = self.story_cls.from_names(["language_model"])
    benchmark = self.benchmark_cls(stories)

    probe_results: dict[str, Any] = {}
    repetitions = 1
    active_browsers = self.browsers[:1]
    for _ in range(repetitions):
      for browser in active_browsers:
        self._setup_run_js_expect(browser, probe_results, status="failed")

    for browser in active_browsers:
      browser.expected_js = copy.deepcopy(browser.expected_js)

    runner = Runner(
      self.out_dir,
      active_browsers,
      benchmark,
      env_config=EnvConfig(),
      env_validation_mode=ValidationMode.SKIP,
      platform=self.platform,
      repetitions=repetitions,
      throw=True,
      in_memory_result_db=True,
    )

    with mock.patch.object(self.benchmark_cls, "validate_url") as cm:
      with self.assertRaises(ValueError) as cm_err:
        runner.run()
      self.assertIn(
        "Blink-AI Benchmark did not finish successfully",
        str(cm_err.exception),
      )
    cm.assert_called_once()

    for browser in active_browsers:
      self.assertSequenceEqual(browser.expected_js, [])

  def test_multimodal_stories(self):
    stories = self.story_cls.from_names(
      ["multimodal_image", "multimodal_audio"]
    )
    self.assertEqual(len(stories), 1)
    story = stories[0]
    self.assertDictEqual(
      story.url_params,
      {
        "api": "language_model",
        "stories": "multimodal_image,multimodal_audio",
      },
    )
    self.assertEqual(
      story.test_url,
      self.story_cls.URL
      + "?api=language_model&stories=multimodal_image%2Cmultimodal_audio",
    )

  def test_substories_and_default(self):
    default_stories = self.story_cls.default_story_names()
    self.assertEqual(
      default_stories,
      (
        "language_model",
        "multimodal_image",
        "multimodal_images",
        "multimodal_audio",
      ),
    )
    for opt_in_story in (
      "mtp_summary",
      "mtp_flight",
      "mtp_emoji",
      "mtp_constrained_summary",
      "tool_calling",
    ):
      self.assertIn(opt_in_story, self.story_cls.SUBSTORIES)
      self.assertNotIn(opt_in_story, default_stories)

    base_features = LANGUAGE_MODEL_API.base_features

    default_story = self.story_cls.default()[0]
    self.assertEqual(default_story.name, "language_model")
    self.assertEqual(default_story.required_features, base_features)
    default_flags = self.benchmark_cls.extra_flags(
      self.browsers[0].attributes(), default_story
    )
    self.assertIn(
      "OnDeviceModelIdleTimeout:on_device_model_idle_timeout/10s",
      str(default_flags),
    )
    self.assertIn("OnDeviceAiDefaultEnabled", str(default_flags))
    self.assertNotIn("OnDeviceModelSpeculativeDecoding", str(default_flags))
    self.assertNotIn("AIPromptAPIToolUse", str(default_flags))

    mtp_story_obj = self.story_cls.from_names(["mtp_summary"])[0]
    self.assertEqual(mtp_story_obj.name, "language_model_mtp_summary")
    self.assertEqual(
      mtp_story_obj.required_features,
      base_features + ("OnDeviceModelSpeculativeDecoding",),
    )
    mtp_flags = self.benchmark_cls.extra_flags(
      self.browsers[0].attributes(), mtp_story_obj
    )
    self.assertIn("OnDeviceModelSpeculativeDecoding", str(mtp_flags))
    self.assertNotIn("AIPromptAPIToolUse", str(mtp_flags))

    tool_use_story_obj = self.story_cls.from_names(["tool_calling"])[0]
    self.assertEqual(
      tool_use_story_obj.required_features,
      base_features
      + (
        "AIPromptAPIToolUse",
        "OnDeviceModelConversationBackend",
        "AIApiFoundationalModel:model_version/v4",
      ),
    )
    tool_use_flags = self.benchmark_cls.extra_flags(
      self.browsers[0].attributes(), tool_use_story_obj
    )
    self.assertIn("AIPromptAPIToolUse", str(tool_use_flags))
    self.assertIn("OnDeviceModelConversationBackend", str(tool_use_flags))
    self.assertIn(
      "AIApiFoundationalModel:model_version/v4",
      str(tool_use_flags),
    )
    self.assertNotIn("OnDeviceModelSpeculativeDecoding", str(tool_use_flags))

  def test_mtp_stories(self):
    stories = self.story_cls.from_names(
      ["mtp_summary", "mtp_flight", "mtp_emoji"]
    )
    self.assertEqual(len(stories), 1)
    story = stories[0]
    self.assertEqual(
      story.required_features,
      LANGUAGE_MODEL_API.base_features + ("OnDeviceModelSpeculativeDecoding",),
    )
    self.assertDictEqual(
      story.url_params,
      {
        "api": "language_model",
        "stories": "mtp_summary,mtp_flight,mtp_emoji",
      },
    )
    self.assertEqual(
      story.test_url,
      self.story_cls.URL + "?api=language_model"
      "&stories=mtp_summary%2Cmtp_flight%2Cmtp_emoji",
    )

  def test_mtp_constrained_story(self):
    name = "mtp_constrained_summary"
    self.assertIn(name, LANGUAGE_MODEL_API.substories)
    self.assertNotIn(name, self.story_cls.default_story_names())
    story = self.story_cls.from_names([name])[0]
    self.assertEqual(
      story.required_features,
      LANGUAGE_MODEL_API.base_features + ("OnDeviceModelSpeculativeDecoding",),
    )
    self.assertDictEqual(
      story.url_params,
      {
        "api": "language_model",
        "stories": name,
      },
    )
    flags = self.benchmark_cls.extra_flags(self.browsers[0].attributes(), story)
    self.assertIn("OnDeviceModelSpeculativeDecoding", str(flags))

  def test_tool_use_stories(self):
    stories = self.story_cls.from_names(["tool_calling"])
    self.assertEqual(len(stories), 1)
    story = stories[0]
    self.assertEqual(
      story.required_features,
      LANGUAGE_MODEL_API.base_features
      + (
        "AIPromptAPIToolUse",
        "OnDeviceModelConversationBackend",
        "AIApiFoundationalModel:model_version/v4",
      ),
    )
    self.assertDictEqual(
      story.url_params,
      {
        "api": "language_model",
        "stories": "tool_calling",
      },
    )
    self.assertEqual(
      story.test_url,
      self.story_cls.URL + "?api=language_model&stories=tool_calling",
    )

  def test_api_config_and_model_selection(self) -> None:
    story_v4 = self.story_cls.from_names(["language_model"], model="v4")[0]
    self.assertEqual(story_v4.name, "language_model_language_model")
    self.assertEqual(story_v4.model, "v4")
    self.assertEqual(
      story_v4.required_features,
      LANGUAGE_MODEL_API.base_features
      + (
        "OnDeviceModelConversationBackend",
        "AIApiFoundationalModel:model_version/v4",
      ),
    )

    tool_v4 = self.story_cls.from_names(["tool_calling"], model="v4")[0]
    self.assertEqual(tool_v4.model, "v4")
    with self.assertRaises(ValueError):
      self.story_cls.from_names(["tool_calling"], model="default")
    with self.assertRaises(ValueError):
      self.story_cls.from_names(["language_model"], model="unknown_model")

  def test_story_filter_cohort_validation(self) -> None:
    self.assertIs(self.benchmark_cls.STORY_FILTER_CLS, BlinkAIStoryFilter)
    self.assertIn("language_model", BlinkAIStoryFilter.api_configs_help())
    self.assertEqual(BlinkAIStoryFilter.model_choices(), ("default", "v4"))
    self.assertTrue(self.benchmark_cls.cli_description())
    with self.assertRaises(ValueError):
      BlinkAIStoryFilter.parse_api_names("language_model,language_model")
    with self.assertRaises(ValueError):
      BlinkAIStoryFilter.parse_api_names(())

    compatible_filter = self.story_filter(
      ["mtp_summary", "mtp_flight"], separate=False
    )
    self.assertEqual(len(compatible_filter.stories), 1)

    with self.assertRaises(ValueError):
      self.story_filter(["language_model", "mtp_summary"], separate=False)

    args_conflict = self.parse_args(
      "--stories=language_model,tool_calling", "--combined"
    )
    with self.assertRaises(ValueError):
      self.benchmark_cls.from_cli_args(args_conflict)

    args_separate = self.parse_args(
      "--stories=language_model,mtp_summary,tool_calling",
      "--separate",
      "--api=language_model",
    )
    benchmark = self.benchmark_cls.from_cli_args(args_separate)
    self.assertEqual(len(benchmark.stories), 3)

    single_neg_args = self.parse_args(
      "--stories=default,-multimodal_audio,-multimodal_images"
    )
    single_neg_bm = self.benchmark_cls.from_cli_args(single_neg_args)
    self.assertEqual(
      single_neg_bm.stories[0].substories,
      ("language_model", "multimodal_image"),
    )

    with self.assertRaises(ValueError):
      compatible_filter.filter_by_name("default")

  def test_cli_model_argument(self) -> None:
    args = self.parse_args("--stories=language_model", "--model=v4")
    benchmark = self.benchmark_cls.from_cli_args(args)
    self.assertEqual(len(benchmark.stories), 1)
    story = benchmark.stories[0]
    assert isinstance(story, BlinkAIStory)
    self.assertEqual(story.model, "v4")
    flags = self.benchmark_cls.extra_flags(self.browsers[0].attributes(), story)
    self.assertIn("AIApiFoundationalModel:model_version/v4", str(flags))

    tool_v4_args = self.parse_args("--stories=tool_calling", "--model=v4")
    tool_v4_benchmark = self.benchmark_cls.from_cli_args(tool_v4_args)
    self.assertEqual(len(tool_v4_benchmark.stories), 1)
    self.assertEqual(
      tool_v4_benchmark.stories[0].name, "language_model_tool_calling"
    )

    tool_conflict_args = self.parse_args(
      "--stories=tool_calling", "--model=default"
    )
    with self.assertRaises(ValueError):
      self.benchmark_cls.from_cli_args(tool_conflict_args)

  def test_custom_api_config_and_setup_js_global(self) -> None:
    writer_api = BlinkAIApiConfig.create(
      name="writer",
      js_global="Writer",
      base_features=("AIWriterAPI",),
      default_model="v1",
      default_substories=("short", "long"),
      models=(BlinkAIModelConfig("v1", features=("WriterModelV1",)),),
      substories=(
        BlinkAISubstoryConfig("short", features=("FeatureA", "FeatureB")),
        BlinkAISubstoryConfig("long", features=("FeatureB", "FeatureA")),
        BlinkAISubstoryConfig("extra", features=("FeatureA", "FeatureB")),
      ),
    )
    self.assertEqual(
      writer_api.resolve_features(),
      ("AIWriterAPI", "WriterModelV1"),
    )
    writer_api.validate_combined_substories(("short", "long"))

    patched_configs = immutabledict(
      {
        **API_CONFIGS,
        "writer": writer_api,
      }
    )
    with mock.patch(
      "crossbench.benchmarks.blink_ai.config.registry.API_CONFIGS",
      patched_configs,
    ):
      default_stories = self.story_cls.default(api_name="writer")
      self.assertEqual(len(default_stories), 1)
      story = default_stories[0]
      self.assertTrue(story.has_default_substories)
      self.assertEqual(story.name, "writer")
      self.assertEqual(
        story.url_params,
        {
          "api": "writer",
          "stories": "short,long",
        },
      )

      all_stories = self.story_cls.all(separate=False, api_name="writer")
      self.assertEqual(len(all_stories), 1)
      self.assertEqual(all_stories[0].name, "writer_all")
      self.assertFalse(all_stories[0].has_default_substories)

      short_story = self.story_cls.from_names(["short"], api_name="writer")[0]
      self.assertEqual(short_story.name, "writer_short")
      long_story = self.story_cls.from_names(["long"], api_name="writer")[0]
      self.assertEqual(long_story.name, "writer_long")
      long_name = "writer_" + ("substory_" * 30)
      cropped_name = short_story._crop_name(long_name)
      self.assertEqual(len(cropped_name), MAX_STORY_NAME_LEN)
      self.assertTrue(cropped_name.startswith(long_name[:55]))
      self.assertEqual(cropped_name, short_story._crop_name(long_name))

      multi_args = self.parse_args("--api=language_model,writer")
      multi_benchmark = self.benchmark_cls.from_cli_args(multi_args)
      self.assertEqual(
        len(multi_benchmark.stories),
        len(LANGUAGE_MODEL_API.default_substories)
        + len(writer_api.default_substories),
      )

      all_api_args = self.parse_args("--api=all")
      all_api_benchmark = self.benchmark_cls.from_cli_args(all_api_args)
      self.assertEqual(
        len(all_api_benchmark.stories),
        len(LANGUAGE_MODEL_API.default_substories)
        + len(writer_api.default_substories),
      )

      all_api_sep_args = self.parse_args("--api=all", "--separate")
      all_api_sep_benchmark = self.benchmark_cls.from_cli_args(all_api_sep_args)
      self.assertEqual(
        len(all_api_sep_benchmark.stories),
        len(LANGUAGE_MODEL_API.default_substories)
        + len(writer_api.default_substories),
      )

      with self.assertRaises(argparse.ArgumentTypeError):
        self.benchmark_cls.from_cli_args(
          self.parse_args("--api=language_model,writer", "--combined")
        )

      qualified_subset_args = self.parse_args(
        "--api=language_model,writer",
        "--stories=language_model:mtp_summary,writer:short",
      )
      qualified_subset_bm = self.benchmark_cls.from_cli_args(
        qualified_subset_args
      )
      self.assertEqual(
        tuple(s.name for s in qualified_subset_bm.stories),
        ("language_model_mtp_summary", "writer_short"),
      )

      for neg_pattern in ("writer:-long", "-writer:-long", "-writer:long"):
        neg_bm = self.benchmark_cls.from_cli_args(
          self.parse_args(
            "--api=language_model,writer",
            f"--stories=writer:default,{neg_pattern}",
          )
        )
        self.assertEqual(
          tuple(s.name for s in neg_bm.stories),
          ("writer_short",),
        )

      with self.assertRaises(ValueError):
        self.benchmark_cls.from_cli_args(
          self.parse_args(
            "--api=language_model,writer",
            "--stories=writer:short,-writer:short",
          )
        )
      with self.assertRaises(ValueError):
        self.benchmark_cls.from_cli_args(
          self.parse_args("--api=writer", "--stories=writer:")
        )

      multi_filter = self.story_filter(
        ["default"],
        separate=True,
        api_names=("language_model", "writer"),
      )
      assert isinstance(multi_filter, BlinkAIStoryFilter)
      from_names_stories = multi_filter.stories_from_names(
        ("language_model:mtp_summary", "writer:short")
      )
      self.assertEqual(
        tuple(s.name for s in from_names_stories),
        ("language_model_mtp_summary", "writer_short"),
      )
      with self.assertRaises(ValueError):
        multi_filter.stories_from_names(("short",))
      with self.assertRaises(ValueError):
        self.story_filter(
          ["default"],
          separate=False,
          api_names=("language_model", "writer"),
        )

      with self.assertRaises(ValueError):
        self.benchmark_cls.from_cli_args(
          self.parse_args(
            "--api=language_model,writer", "--stories=mtp_summary"
          )
        )
      with self.assertRaises(ValueError):
        self.benchmark_cls.from_cli_args(
          self.parse_args("--api=language_model", "--stories=writer:short")
        )
      with self.assertRaises(ValueError):
        self.benchmark_cls.from_cli_args(
          self.parse_args("--api=language_model", "--stories=:short")
        )

      with self.assertRaises(argparse.ArgumentTypeError):
        self.benchmark_cls.from_cli_args(
          self.parse_args("--api=language_model,writer", "--model=v4")
        )
      with self.assertRaises(ValueError):
        self.story_filter(
          ["default"],
          separate=True,
          api_names=("language_model", "writer"),
          model="v4",
        )
      with self.assertRaises(argparse.ArgumentError):
        self.parse_args("--api=all,writer")

      mock_actions = mock.MagicMock()
      mock_actions.__enter__.return_value = mock_actions
      mock_run = mock.Mock()
      mock_run.actions = mock.MagicMock(return_value=mock_actions)
      story.setup(mock_run)
      mock_actions.wait_js_condition.assert_called_once_with(
        "return !!window.Writer && window.testStatus === 'waiting'",
        0.5,
        timeout=dt.timedelta(seconds=45),
      )

      mock_actions.wait_js_condition.side_effect = TimeoutError("timed out")
      with self.assertRaises(RuntimeError) as cm_err:
        story.setup(mock_run)
      self.assertIn("window.Writer", str(cm_err.exception))
      self.assertIn("within 45 seconds.", str(cm_err.exception))

  def test_vram_probe_context_single_gpu(self):
    samples = [
      {
        "gpu_0": 100.0,
      },
      {
        "gpu_0": 150.0,
      },
      {
        "gpu_0": 200.0,
      },
      {
        "gpu_0": 120.0,
      },
    ]
    data = self._run_vram_probe_context(samples, {"downloadTimeMs": 10.0})
    self.assertEqual(data["downloadTimeMs"], 10.0)
    self._assert_vram_stats(data, peak_mb=200.0, baseline_mb=100.0)
    self._assert_vram_stats(
      data, peak_mb=200.0, baseline_mb=100.0, gpu_id="gpu_0"
    )

  def test_vram_probe_context_multi_gpu(self):
    samples = [
      {
        "gpu_0": 100.0,
        "gpu_1": 200.0,
      },
      {
        "gpu_0": 150.0,
        "gpu_1": 250.0,
      },
      {
        "gpu_0": 300.0,
        "gpu_1": 220.0,
      },
      {
        "gpu_0": 100.0,
        "gpu_1": 200.0,
      },
    ]
    data = self._run_vram_probe_context(
      samples, {"sessionCreationTimeMs": 50.0}
    )
    self.assertEqual(data["sessionCreationTimeMs"], 50.0)
    self._assert_vram_stats(data, peak_mb=550.0, baseline_mb=300.0)
    self._assert_vram_stats(
      data,
      peak_mb=300.0,
      baseline_mb=100.0,
      gpu_id="gpu_0",
      check_flat_gpu=True,
    )
    self._assert_vram_stats(
      data,
      peak_mb=250.0,
      baseline_mb=200.0,
      gpu_id="gpu_1",
      check_flat_gpu=True,
    )

  def test_vram_probe_context_no_gpu(self):
    data = self._run_vram_probe_context([{}], {"downloadTimeMs": 10.0})
    self.assertEqual(data, {"downloadTimeMs": 10.0})

  def test_vram_probe_config_parser(self):
    parser = BlinkAIProbe.config_parser()
    probe = parser.parse({"vram_interval": "2s"})
    self.assertEqual(probe.vram_interval, dt.timedelta(seconds=2))

  def test_vram_probe_invalid_interval(self):
    with self.assertRaises(ValueError):
      BlinkAIProbe(vram_interval=dt.timedelta(seconds=0.01))

  def test_run_with_vram(self):
    stories = self.story_cls.from_names(["language_model"])
    benchmark = self.benchmark_cls(stories)
    probe_results = {"downloadTimeMs": 500.5, **SAMPLE_STORY_METRICS}

    for browser in self.browsers:
      self._setup_run_js_expect(browser, probe_results)
      browser.expected_js = copy.deepcopy(browser.expected_js)

    self.platform.gpu_vram_used = mock.Mock(
      side_effect=[
        {
          "gpu_0": 100.0,
        },
        {
          "gpu_0": 250.0,
        },
      ]
      + [
        {
          "gpu_0": 150.0,
        }
      ]
      * 20
    )

    runner = Runner(
      self.out_dir,
      self.browsers,
      benchmark,
      env_config=EnvConfig(),
      env_validation_mode=ValidationMode.SKIP,
      platform=self.platform,
      repetitions=1,
      throw=True,
      in_memory_result_db=True,
    )

    with mock.patch.object(self.benchmark_cls, "validate_url") as cm:
      runner.run()
    cm.assert_called_once()

    expected_vram_keys = tuple(
      f"vram_{stat}_{unit}"
      for stat in VRAM_STAT_NAMES
      for unit in ("mb", "bytes")
    )
    summary_file = self.out_dir / "blink_ai.json"
    self.assertTrue(summary_file.exists())
    summary_content = json.loads(summary_file.read_text())
    for browser in self.browsers:
      browser_data = summary_content[browser.unique_name]["data"]
      for key in expected_vram_keys:
        self.assertIn(key, browser_data)
      self.assertIn("vram/peak_mb", browser_data)

    story_json_files = [
      f for f in self.out_dir.glob("**/blink_ai.json") if f != summary_file
    ]
    self.assertTrue(len(story_json_files) > 0)
    for json_file in story_json_files:
      content = json.loads(json_file.read_text())
      for key in expected_vram_keys:
        self.assertIn(key, content)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
