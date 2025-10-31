# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json

from crossbench import exception
from crossbench.pinpoint.api import PINPOINT_CANCEL_JOB_API_URL
from crossbench.pinpoint.auth import get_auth_session


def cancel_job(job_id: str, reason: str) -> None:
  """Cancels a Pinpoint job."""
  authed_session = get_auth_session()
  payload = {
      "job_id": job_id,
      "reason": reason,
  }
  with exception.annotate("Cancelling a Pinpoint job"):
    response = authed_session.post(PINPOINT_CANCEL_JOB_API_URL, data=payload)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))
