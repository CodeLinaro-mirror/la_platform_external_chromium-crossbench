# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
from functools import cache

from crossbench.pinpoint.api import PINPOINT_START_JOB_API_URL
from crossbench.pinpoint.auth import get_auth_session
from crossbench.pinpoint.helper import annotate
from crossbench.pinpoint.list_builds import fetch_builds


def start_job(
    benchmark: str,
    bot: str,
    story: str | None = None,
    story_tags: str | None = None,
    repeat: int = 10,
    bug_id: str | None = None,
    base_commit: str = "HEAD",
    exp_commit: str | None = None,
    base_patch_url: str | None = None,
    exp_patch_url: str | None = None,
    base_js_flags: str | None = None,
    exp_js_flags: str | None = None,
    base_enable_features: str | None = None,
    exp_enable_features: str | None = None,
    base_disable_features: str | None = None,
    exp_disable_features: str | None = None,
) -> None:
  """Starts a new Pinpoint job."""
  exp_commit = exp_commit or base_commit

  authed_session = get_auth_session()

  payload = {
      "comparison_mode":
          "try",
      "benchmark":
          benchmark,
      "configuration":
          bot,
      "story":
          story,
      "story_tags":
          story_tags,
      "initial_attempt_count":
          repeat,
      "bug_id":
          bug_id,
      "base_git_hash":
          _convert_recent_build_to_hash(base_commit, bot),
      "end_git_hash":
          _convert_recent_build_to_hash(exp_commit, bot),
      "base_patch":
          base_patch_url,
      "experiment_patch":
          exp_patch_url,
      "base_extra_args":
          _combine_extra_browser_args(
              js_flags=base_js_flags,
              enable_features=base_enable_features,
              disable_features=base_disable_features),
      "experiment_extra_args":
          _combine_extra_browser_args(
              js_flags=exp_js_flags,
              enable_features=exp_enable_features,
              disable_features=exp_disable_features),
  }
  with annotate("Starting Pinpoint job"):
    response = authed_session.post(PINPOINT_START_JOB_API_URL, data=payload)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


def _convert_recent_build_to_hash(commit: str, bot: str) -> str:
  return _fetch_recent_build(bot) if commit == "recent" else commit


@cache
def _fetch_recent_build(bot: str) -> str:
  return fetch_builds(bot)[0].commit


def _combine_extra_browser_args(js_flags: str | None,
                                enable_features: str | None,
                                disable_features: str | None) -> str | None:
  """
    Combines command line arguments for Chrome into a single string.

    The arguments are formatted as:
    --extra-browser-args="--js-flags={js_flags} --enable-features=..."
    """
  args = [
      _format_arg("js-flags", js_flags),
      _format_arg("enable-features", enable_features),
      _format_arg("disable-features", disable_features),
  ]
  extra_browser_args = [arg for arg in args if arg is not None]
  if extra_browser_args:
    return f'--extra-browser-args="{" ".join(extra_browser_args)}"'
  return None


def _format_arg(key: str, value: str | None) -> str | None:
  if value:
    return f"--{key}={value}"
  return None
