# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime
from typing import Any

import requests
from google import auth as google_auth
from google.auth.transport import requests as auth_requests
from tabulate import tabulate

from crossbench import plt
from crossbench.cli import ui

PINPOINT_JOBS_API_URL = "https://pinpoint-dot-chromeperf.appspot.com/api/jobs"


def list_jobs() -> None:
  authed_session = _get_auth_session()

  try:
    response = authed_session.get(PINPOINT_JOBS_API_URL)
    response.raise_for_status()
    data = response.json()
    jobs = data.get("jobs", [])
    if not jobs:
      print("No jobs found.")
      return
    _display_jobs_table(jobs)
  except requests.exceptions.RequestException as e:
    print(f"An error occurred while fetching jobs: {e}")


def _get_auth_session() -> auth_requests.AuthorizedSession:
  try:
    # TODO(b/455510346): Make sure it supports @chromium.org accounts.
    credentials, _ = google_auth.default(
        scopes=["https://www.googleapis.com/auth/userinfo.email"])
    return auth_requests.AuthorizedSession(credentials)
  except google_auth.exceptions.DefaultCredentialsError:
    user_input = ui.prompt(
        "Authentication failed. Please run 'gcloud auth application-default login' "
        "to configure your credentials.\n"
        "Would you like to run it now?", "[Y/n] ").lower().strip()
    if user_input in ["", "y", "yes"]:
      plt.PLATFORM.sh(
          "gcloud", "auth", "application-default", "login", check=True)
      return _get_auth_session()
    raise


def _display_jobs_table(jobs: list[dict[str, Any]]) -> None:
  headers = [
      "Job ID", "Job Name", "Benchmark", "Configuration", "Owner",
      "Created Time", "Status"
  ]
  table_data = []

  for job in jobs:
    created_time = job.get("created")
    if created_time:
      dt_object = datetime.datetime.fromisoformat(
          created_time.replace("Z", "+00:00"))
      created_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")

    row = [
        job.get("job_id", ""),
        job.get("name", ""),
        job.get("arguments", {}).get("benchmark", ""),
        job.get("configuration", ""),
        job.get("user", ""),
        created_time,
        job.get("status", ""),
    ]
    table_data.append([_truncate(cell) for cell in row])
  print(tabulate(table_data, headers=headers))


def _truncate(text: str, max_length: int = 50) -> str:
  text = str(text)
  if len(text) > max_length:
    return text[:max_length - 3] + "..."
  return text
