# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
import logging
from typing import Sequence

from crossbench.exception import ExceptionAnnotator
from crossbench.pinpoint import http_requests
from crossbench.pinpoint.api import PINPOINT_CANCEL_JOB_API_URL
from crossbench.pinpoint.helper import annotate


def cancel_job(job_id: str, reason: str) -> None:
  """Cancels a Pinpoint job."""
  payload = {
      "job_id": job_id,
      "reason": reason,
  }
  with annotate("Cancelling Pinpoint job"):
    response = http_requests.post(PINPOINT_CANCEL_JOB_API_URL, data=payload)
    response.raise_for_status()
  logging.info(json.dumps(response.json(), indent=2))


def cancel_jobs(job_ids: Sequence[str], reason: str) -> None:
  """Cancels multiple Pinpoint jobs."""
  # Continue cancelling remaining jobs even if cancelling one fails.
  with ExceptionAnnotator().annotate("Cancelling Pinpoint jobs") as exceptions:
    for job_id in job_ids:
      logging.info("Cancelling job: %s", job_id)
      with exceptions.capture(f"Cancelling job: {job_id}"):
        cancel_job(job_id=job_id, reason=reason)
