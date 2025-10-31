# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
import sys

import requests

from crossbench.pinpoint.api import PINPOINT_JOB_API_URL_TEMPLATE
from crossbench.pinpoint.auth import get_auth_session


def job_config(job_id: str) -> None:
  """Fetches and displays the configuration for a specific Pinpoint job."""
  authed_session = get_auth_session()
  url = PINPOINT_JOB_API_URL_TEMPLATE.format(job_id=job_id)
  try:
    response = authed_session.get(url)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))
  except requests.exceptions.RequestException as e:
    print(
        f"An error occurred while fetching job configuration for '{job_id}': {e}",
        file=sys.stderr)
    sys.exit(1)
