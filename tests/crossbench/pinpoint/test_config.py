# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
from typing import Final
from unittest import mock

from crossbench.cli.config.flags import FlagsConfig
from crossbench.pinpoint.config import PinpointTryJobConfig, VariantConfig
from crossbench.pinpoint.list_builds import Build
from tests import test_helper
from tests.crossbench.pinpoint.auth_session_mixin import MockAuthSessionMixin

_TEST_PATCH: Final[
    str] = "https://chromium-review.googlesource.com/c/crossbench/+/12345"
_TEST_PATCH2: Final[
    str] = "https://chromium-review.googlesource.com/c/crossbench/+/111/2"


class VariantConfigTest(MockAuthSessionMixin):
  _get_auth_session_patch_target = "crossbench.pinpoint.auth.get_auth_session"

  def setUp(self):
    super().setUp()
    self.mock_fetch_builds = self.enterContext(
        mock.patch("crossbench.pinpoint.config.fetch_builds"))
    self.mock_fetch_builds.return_value = [
        Build(commit="aaaabbbb", date="2025-11-01 00:00:00"),
    ]

  def test_parse_variant(self):
    variant = VariantConfig.parse(
        json.dumps({
            "commit": "abcd1234",
            "patch": _TEST_PATCH,
            "flags": "--test-flag --js-flags=--base-js-flag",
        }))
    self.assertEqual(variant.commit, "abcd1234")
    self.assertEqual(variant.patch, _TEST_PATCH)
    self.assertDictEqual(variant.flags_as_dict(), {
        "--test-flag": None,
        "--js-flags": "--base-js-flag"
    })

  def test_parse_variant_default(self):
    variant = VariantConfig.parse("{}")
    self.assertEqual(variant.commit, "HEAD")
    self.assertIsNone(variant.patch)
    self.assertEqual(variant.flags_as_str(), "")
    self.assertDictEqual(variant.flags_as_dict(), {})

  def test_parse_commit(self):
    self.assertEqual(VariantConfig.parse_commit("HEAD"), "HEAD")
    self.assertEqual(VariantConfig.parse_commit("-HEAD"), "HEAD")
    self.assertEqual(VariantConfig.parse_commit(""), "HEAD")
    self.assertEqual(VariantConfig.parse_commit("recent"), "recent")
    self.assertEqual(VariantConfig.parse_commit("abcdef00"), "abcdef00")
    self.assertEqual(VariantConfig.parse_commit("1234ABCD"), "1234abcd")
    with self.assertRaises(ValueError):
      VariantConfig.parse_commit("invalid")
    with self.assertRaises(ValueError):
      VariantConfig.parse_commit("1234567")
    with self.assertRaises(ValueError):
      VariantConfig.parse_commit("1" * 41)

  def test_parse_patch(self):
    self.assertEqual(VariantConfig.parse_patch(_TEST_PATCH), _TEST_PATCH)

    with self.assertRaises(ValueError):
      VariantConfig.parse_patch("invalid")

  def test_override_commit(self):
    config = VariantConfig()
    config.override_commit("abcdef00", bot="test_bot")
    self.assertEqual(config.commit, "abcdef00")

    config.override_commit(None, bot="test_bot")
    self.assertEqual(config.commit, "abcdef00")

    config.override_commit("recent", bot="test_bot")
    self.assertEqual(config.commit, "aaaabbbb")
    self.mock_fetch_builds.assert_called_once_with("test_bot")

  def test_override_patch(self):
    config = VariantConfig()
    config.override_patch(_TEST_PATCH)
    self.assertEqual(config.patch, _TEST_PATCH)

    config.override_patch(None)
    self.assertEqual(config.patch, _TEST_PATCH)

  def test_override_empty_flags(self):
    config = VariantConfig()
    config.override_flags(
        js_flags="--js-flag1,--js-flag2",
        enable_features="enablefeature1,enablefeature2",
        disable_features="disablefeature1,disablefeature2")
    self.assertDictEqual(
        config.flags_as_dict(), {
            "--js-flags": "--js-flag1,--js-flag2",
            "--enable-features": "enablefeature1,enablefeature2",
            "--disable-features": "disablefeature1,disablefeature2",
        })

  def test_override_existing_flags(self):
    config = VariantConfig.parse(
        "{flags: '--standalone --js-flags=--js-flag0 "
        "--enable-features=enablefeature0 --disable-features=disablefeature0'}")
    config.override_flags(
        js_flags="--js-flag1,--js-flag2",
        enable_features="enablefeature1,enablefeature2",
        disable_features="disablefeature1,disablefeature2")
    self.assertDictEqual(
        config.flags_as_dict(), {
            "--standalone": None,
            "--js-flags": "--js-flag1,--js-flag2",
            "--enable-features": "enablefeature1,enablefeature2",
            "--disable-features": "disablefeature1,disablefeature2",
        })

  def test_override_with_none_flags(self):
    config = VariantConfig.parse(
        "{flags: '--standalone --js-flags=--js-flag0 "
        "--enable-features=enablefeature0 --disable-features=disablefeature0'}")
    config.override_flags()
    self.assertDictEqual(
        config.flags_as_dict(), {
            "--standalone": None,
            "--js-flags": "--js-flag0",
            "--enable-features": "enablefeature0",
            "--disable-features": "disablefeature0",
        })


class PinpointTryJobConfigTest(MockAuthSessionMixin):
  _get_auth_session_patch_target = "crossbench.pinpoint.auth.get_auth_session"

  def setUp(self):
    super().setUp()
    self.mock_fetch_benchmarks = self.enterContext(
        mock.patch("crossbench.pinpoint.config.fetch_benchmarks"))
    self.mock_fetch_benchmarks.return_value = ["test_benchmark"]
    self.mock_fetch_bots = self.enterContext(
        mock.patch("crossbench.pinpoint.config.fetch_bots"))
    self.mock_fetch_bots.return_value = ["test_bot"]
    self.mock_fetch_stories = self.enterContext(
        mock.patch("crossbench.pinpoint.config.fetch_stories"))
    self.mock_fetch_stories.return_value = ["test_story"]
    self.mock_fetch_builds = self.enterContext(
        mock.patch("crossbench.pinpoint.config.fetch_builds"))
    self.mock_fetch_builds.return_value = [
        Build(commit="aaaabbbb", date="2025-11-02 00:00:00"),
    ]
    self.mock_show_warnings = self.enterContext(
        mock.patch("crossbench.pinpoint.config.show_warnings"))

  def test_parse_minimal_config(self):
    config = PinpointTryJobConfig.parse_and_override(
        config=json.dumps({
            "benchmark": "test_benchmark",
            "bot": "test_bot",
            "story": "test_story",
        }))
    self.assertEqual(
        config,
        PinpointTryJobConfig(
            benchmark="test_benchmark",
            bot="test_bot",
            story="test_story",
            base=VariantConfig(),
            experiment=VariantConfig(),
        ))

  def test_parse_all_fields(self):
    config = PinpointTryJobConfig.parse_and_override(
        config=json.dumps({
            "benchmark": "test_benchmark",
            "bot": "test_bot",
            "story": "test_story",
            "story_tags": "tag1,tag2",
            "repeat": 42,
            "bug": 67890,
            "base": {
                "commit": "abcdef00",
                "patch": _TEST_PATCH,
                "flags": "--js-flags=--base-js-flag",
            },
            "experiment": {
                "commit": "aaaabbbb",
                "patch": _TEST_PATCH2,
                "flags": "--js-flags=--exp-js-flag",
            },
        }))
    self.assertEqual(
        config,
        PinpointTryJobConfig(
            benchmark="test_benchmark",
            bot="test_bot",
            story="test_story",
            story_tags="tag1,tag2",
            repeat=42,
            bug=67890,
            base=VariantConfig(
                commit="abcdef00",
                patch=_TEST_PATCH,
                flags=FlagsConfig.parse("--js-flags=--base-js-flag"),
            ),
            experiment=VariantConfig(
                commit="aaaabbbb",
                patch=_TEST_PATCH2,
                flags=FlagsConfig.parse("--js-flags=--exp-js-flag"),
            )))

  def test_override_all_fields(self):
    config = PinpointTryJobConfig.parse_and_override(
        benchmark="test_benchmark",
        bot="test_bot",
        story="test_story",
        story_tags="tag1,tag2",
        repeat=42,
        bug=67890,
        base_commit="abcdef00",
        exp_commit="12345678",
        base_patch=_TEST_PATCH,
        exp_patch=_TEST_PATCH2,
        base_js_flags="--base-js-flag",
        exp_js_flags="--exp-js-flag",
        base_enable_features="enable1,enable2",
        exp_enable_features="enable3,enable4",
        base_disable_features="disable1,disable2",
        exp_disable_features="disable3,disable4",
    )
    self.assertEqual(
        config,
        PinpointTryJobConfig(
            benchmark="test_benchmark",
            bot="test_bot",
            story="test_story",
            story_tags="tag1,tag2",
            repeat=42,
            bug=67890,
            base=VariantConfig(
                commit="abcdef00",
                patch=_TEST_PATCH,
                flags=FlagsConfig.parse("--js-flags=--base-js-flag "
                                        "--enable-features=enable1,enable2 "
                                        "--disable-features=disable1,disable2"),
            ),
            experiment=VariantConfig(
                commit="12345678",
                patch=_TEST_PATCH2,
                flags=FlagsConfig.parse("--js-flags=--exp-js-flag "
                                        "--enable-features=enable3,enable4 "
                                        "--disable-features=disable3,disable4"),
            )))

  def test_parse_and_override_missing_benchmark(self):
    with self.assertRaises(ValueError):
      PinpointTryJobConfig.parse_and_override(config="{bot: 'test_bot'}")
    with self.assertRaises(ValueError):
      PinpointTryJobConfig.parse_and_override(bot="test_bot")

  def test_parse_and_override_missing_bot(self):
    with self.assertRaises(ValueError):
      PinpointTryJobConfig.parse_and_override(
          config="{benchmark: 'test_benchmark'}")
    with self.assertRaises(ValueError):
      PinpointTryJobConfig.parse_and_override(benchmark="test_benchmark")

  def test_parse_and_override_missing_story_and_tags(self):
    self.mock_fetch_stories.return_value = []
    with self.assertRaises(ValueError):
      PinpointTryJobConfig.parse_and_override(
          benchmark="test_benchmark", bot="test_bot")

  def test_to_request_json(self):
    config = PinpointTryJobConfig.parse_and_override(
        benchmark="test_benchmark",
        bot="test_bot",
        story="test_story",
        story_tags="tag1,tag2",
        repeat=42,
        bug=12345,
        base_commit="abcdef00",
        exp_commit="12345678",
        base_patch=_TEST_PATCH,
        exp_patch=_TEST_PATCH2,
        base_js_flags="--base-js-flag",
        exp_js_flags="--exp-js-flag",
        base_enable_features="enable1,enable2",
        exp_enable_features="enable3,enable4",
        base_disable_features="disable1,disable2",
        exp_disable_features="disable3,disable4",
    )
    self.assertDictEqual(
        config.to_request_json(), {
            "comparison_mode": "try",
            "benchmark": "test_benchmark",
            "configuration": "test_bot",
            "story": "test_story",
            "story_tags": "tag1,tag2",
            "initial_attempt_count": 42,
            "bug_id": 12345,
            "base_git_hash": "abcdef00",
            "end_git_hash": "12345678",
            "base_patch": _TEST_PATCH,
            "experiment_patch": _TEST_PATCH2,
            "base_extra_args":
                '--extra-browser-args="--js-flags=--base-js-flag '
                '--enable-features=enable1,enable2 '
                '--disable-features=disable1,disable2"',
            "experiment_extra_args":
                '--extra-browser-args="--js-flags=--exp-js-flag '
                '--enable-features=enable3,enable4 '
                '--disable-features=disable3,disable4"',
        })

  def test_to_request_json_no_flags(self):
    config = PinpointTryJobConfig.parse_and_override(
        benchmark="test_benchmark",
        bot="test_bot",
        story="test_story",
    )
    self.assertDictEqual(
        config.to_request_json(), {
            "comparison_mode": "try",
            "benchmark": "test_benchmark",
            "configuration": "test_bot",
            "story": "test_story",
            "story_tags": None,
            "initial_attempt_count": 100,
            "bug_id": None,
            "base_git_hash": "HEAD",
            "end_git_hash": "HEAD",
            "base_patch": None,
            "experiment_patch": None,
            "base_extra_args": None,
            "experiment_extra_args": None,
        })

  def test_parse_and_override_recent_commit(self):
    config = PinpointTryJobConfig.parse_and_override(
        benchmark="test_benchmark",
        bot="test_bot",
        story="test_story",
        base_commit="recent",
        exp_commit="recent")
    self.assertEqual(config.base.commit, "aaaabbbb")
    self.assertEqual(config.experiment.commit, "aaaabbbb")
    self.mock_fetch_builds.assert_called_with("test_bot")

  def test_parse_and_override_empty_commit_to_head(self):
    config = PinpointTryJobConfig.parse_and_override(
        benchmark="test_benchmark",
        bot="test_bot",
        story="test_story",
        base_commit="",
        exp_commit="")
    self.assertEqual(config.base.commit, "HEAD")
    self.assertEqual(config.experiment.commit, "HEAD")

  def test_parse_and_override_story_auto_fetch_signle_story(self):
    config = PinpointTryJobConfig.parse_and_override(
        benchmark="test_benchmark", bot="test_bot")
    self.assertEqual(config.story, "test_story")
    self.mock_fetch_stories.assert_called_once_with("test_benchmark")

  def test_parse_and_override_story_auto_fetch_multiple_stories(self):
    self.mock_fetch_stories.return_value = ["story1", "story2"]
    with self.assertRaises(ValueError):
      PinpointTryJobConfig.parse_and_override(
          benchmark="test_benchmark", bot="test_bot")
    self.mock_fetch_stories.assert_called_once_with("test_benchmark")

  def test_parse_and_override_story_auto_fetch_no_story(self):
    self.mock_fetch_stories.return_value = []
    with self.assertRaises(ValueError):
      PinpointTryJobConfig.parse_and_override(
          benchmark="test_benchmark", bot="test_bot")
    self.mock_fetch_stories.assert_called_once_with("test_benchmark")

  def test_parse_and_override_unknown_benchmark_show_warning(self):
    self.mock_fetch_benchmarks.return_value = ["other_benchmark"]
    PinpointTryJobConfig.parse_and_override(
        benchmark="test_benchmark", bot="test_bot", story="test_story")
    self.mock_show_warnings.assert_called_once_with(
        ["Unknown benchmark: test_benchmark"])

  def test_parse_and_override_unknown_bot_show_warning(self):
    self.mock_fetch_bots.return_value = ["other_bot"]
    PinpointTryJobConfig.parse_and_override(
        benchmark="test_benchmark", bot="test_bot", story="test_story")
    self.mock_show_warnings.assert_called_once_with(["Unknown bot: test_bot"])

  def test_parse_and_override_unknown_story_show_warning(self):
    self.mock_fetch_stories.return_value = ["other_story"]
    PinpointTryJobConfig.parse_and_override(
        benchmark="test_benchmark", bot="test_bot", story="test_story")
    self.mock_show_warnings.assert_called_once_with(
        ["Unknown story: test_story"])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
