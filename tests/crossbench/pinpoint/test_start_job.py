# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import Final
from unittest import mock

import requests

from crossbench.exception import MultiException
from crossbench.pinpoint.api import PINPOINT_START_JOB_API_URL
from crossbench.pinpoint.list_builds import Build
from crossbench.pinpoint.start_job import start_job
from tests import test_helper
from tests.crossbench.pinpoint.auth_session_mixin import MockAuthSessionMixin


class StartJobTest(MockAuthSessionMixin):
  _get_auth_session_patch_target: Final[
      str] = "crossbench.pinpoint.start_job.get_auth_session"

  def setUp(self):
    super().setUp()
    self.mock_fetch_builds = self.enterContext(
        mock.patch("crossbench.pinpoint.start_job.fetch_builds"))
    self.mock_fetch_builds.return_value = [
        Build(commit="recent_hash1", date="2025-11-02 00:00:00"),
        Build(commit="recent_hash2", date="2025-11-01 00:00:00"),
    ]

    def mock_post_side_effect(url, *args, **kwargs):
      self.assertEqual(url, PINPOINT_START_JOB_API_URL,
                       f"Unexpected URL called: {url}")
      mock_response = mock.Mock()
      mock_response.json.return_value = {
          "jobId": "123",
          "jobUrl": "https://example.com/123"
      }
      mock_response.raise_for_status.return_value = None
      return mock_response

    self.mock_session.post.side_effect = mock_post_side_effect
    self.mock_print = self.enterContext(mock.patch("builtins.print"))

  def test_start_job_correct_parameters(self):
    start_job(
        benchmark="test_benchmark",
        bot="test_bot",
        story="test_story",
        story_tags="test_tag",
        repeat=42,
        bug_id="123456789",
        base_commit="HEAD",
        exp_commit="9ed44454",
        base_patch_url="https://base.patch",
        exp_patch_url="https://exp.patch",
        base_js_flags="--base-js-flag",
        exp_js_flags="--exp-js-flag",
        base_enable_features="base_enabled_feature",
        exp_enable_features="exp_enabled_feature",
        base_disable_features="base_disable_feature",
        exp_disable_features="exp_disable_feature",
    )
    expected_payload = {
        "comparison_mode": "try",
        "benchmark": "test_benchmark",
        "configuration": "test_bot",
        "story": "test_story",
        "story_tags": "test_tag",
        "initial_attempt_count": 42,
        "bug_id": "123456789",
        "base_git_hash": "HEAD",
        "end_git_hash": "9ed44454",
        "base_patch": "https://base.patch",
        "experiment_patch": "https://exp.patch",
        "base_extra_args": '--extra-browser-args="--js-flags=--base-js-flag '
                           '--enable-features=base_enabled_feature '
                           '--disable-features=base_disable_feature"',
        "experiment_extra_args":
            '--extra-browser-args="--js-flags=--exp-js-flag '
            '--enable-features=exp_enabled_feature '
            '--disable-features=exp_disable_feature"',
    }
    self.mock_session.post.assert_called_with(
        PINPOINT_START_JOB_API_URL, data=expected_payload)

  def test_start_job_api_error(self):
    self.mock_session.post.side_effect = requests.exceptions.HTTPError(
        "API Error")
    with self.assertRaises(MultiException):
      start_job(benchmark="test_benchmark", bot="test_bot")

  def test_replace_exp_commit_with_base_commit_when_none(self):
    start_job(
        benchmark="test_benchmark",
        bot="test_bot",
        base_commit="123abc",
        exp_commit=None,
    )
    _, params = self.mock_session.post.call_args
    self.assertEqual(params["data"]["end_git_hash"], "123abc")

  def test_replace_commit_with_recent_build(self):
    start_job(
        benchmark="test_benchmark",
        bot="test_bot",
        base_commit="recent",
        exp_commit="recent",
    )
    _, params = self.mock_session.post.call_args
    self.assertEqual(params["data"]["base_git_hash"], "recent_hash1")
    self.assertEqual(params["data"]["end_git_hash"], "recent_hash1")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
