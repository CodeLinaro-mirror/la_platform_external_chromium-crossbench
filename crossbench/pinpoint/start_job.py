# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from crossbench.pinpoint.api import PINPOINT_START_JOB_API_URL
from crossbench.pinpoint.auth import get_auth_session
from crossbench.pinpoint.helper import annotate

if TYPE_CHECKING:
  from crossbench.pinpoint.config import PinpointTryJobConfig


def start_job(
    config: PinpointTryJobConfig,
    base_js_flags: str | None = None,
    exp_js_flags: str | None = None,
    base_enable_features: str | None = None,
    exp_enable_features: str | None = None,
    base_disable_features: str | None = None,
    exp_disable_features: str | None = None,
) -> None:
  """Starts a new Pinpoint job."""
  authed_session = get_auth_session()

  payload = config.to_request_json()
  payload["base_extra_args"] = _combine_extra_browser_args(
      js_flags=base_js_flags,
      enable_features=base_enable_features,
      disable_features=base_disable_features)
  payload["experiment_extra_args"] = _combine_extra_browser_args(
      js_flags=exp_js_flags,
      enable_features=exp_enable_features,
      disable_features=exp_disable_features)
  with annotate("Starting Pinpoint job"):
    response = authed_session.post(PINPOINT_START_JOB_API_URL, data=payload)
    response.raise_for_status()
  print(json.dumps(response.json(), indent=2))


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
