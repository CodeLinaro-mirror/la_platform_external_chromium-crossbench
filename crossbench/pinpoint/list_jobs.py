# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime
import itertools
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Final

import requests
from google import auth as google_auth
from google.auth.transport import requests as auth_requests
from tabulate import tabulate

from crossbench import plt
from crossbench.cli import ui
from crossbench.pinpoint.user import UserEnum

PINPOINT_JOBS_API_URL: Final[
    str] = "https://pinpoint-dot-chromeperf.appspot.com/api/jobs"
USERINFO_API_URL: Final[str] = "https://www.googleapis.com/oauth2/v3/userinfo"
JOB_SHORTEN_URL_TEMPLATE: Final[str] = "http://go/j_/{job_id}"


def list_jobs(user: UserEnum | str, number: int, truncate: int | None) -> None:
  authed_session = _get_auth_session()

  try:
    emails_to_query = _fetch_user_emails(authed_session, user)

    jobs = []
    with ThreadPoolExecutor() as executor:
      results = executor.map(
          lambda email: _fetch_jobs(authed_session, number, email),
          emails_to_query)
      jobs = list(itertools.chain.from_iterable(results))

    jobs.sort(key=lambda job: job.get("created", ""), reverse=True)

    if not jobs:
      print("No jobs found.")
      return

    _display_jobs_table(jobs[:number], user == UserEnum.ALL, truncate)
  except requests.exceptions.RequestException as e:
    print(f"An error occurred while fetching jobs: {e}")


def _fetch_user_emails(authed_session: auth_requests.AuthorizedSession,
                       user: UserEnum | str) -> set[str | None]:
  if user == UserEnum.ME:
    email = _get_user_email(authed_session)
    username = email.split("@")[0]
    return {email, f"{username}@google.com", f"{username}@chromium.org"}
  if user == UserEnum.ALL:
    return {None}
  return {user}


def _fetch_jobs(authed_session: auth_requests.AuthorizedSession,
                number: int,
                email: str | None = None) -> list[dict[str, Any]]:
  jobs = []
  next_cursor = None
  params = {}
  if email:
    params["filter"] = f"user={email}"

  while True:
    if next_cursor:
      params["next_cursor"] = next_cursor

    response = authed_session.get(PINPOINT_JOBS_API_URL, params=params)
    response.raise_for_status()
    data = response.json()
    jobs.extend(data.get("jobs", []))

    if len(jobs) >= number:
      return jobs[:number]

    next_cursor = data.get("next_cursor")
    if not data.get("next") or not next_cursor:
      break
  return jobs


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


def _get_user_email(authed_session: auth_requests.AuthorizedSession) -> str:
  response = authed_session.get(USERINFO_API_URL)
  response.raise_for_status()
  return response.json()["email"]


def _display_jobs_table(jobs: list[dict[str, Any]], all_users: bool,
                        truncate: int | None) -> None:
  headers = [
      "Job URL", "Job Name", "Benchmark", "Configuration", "Created Time",
      "Status"
  ]
  if all_users:
    headers.insert(4, "User")

  table_data = []

  for job in jobs:
    created_time = job.get("created")
    if created_time:
      dt_object = datetime.datetime.fromisoformat(
          created_time.replace("Z", "+00:00"))
      created_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")

    status = job.get("status", "")
    row = [
        JOB_SHORTEN_URL_TEMPLATE.format(job_id=job.get("job_id", "")),
        job.get("name", ""),
        job.get("arguments", {}).get("benchmark", ""),
        job.get("configuration", ""),
        created_time,
        f"{_get_emoji_by_status(status)} {status}",
    ]
    if all_users:
      row.insert(
          4,
          job.get("user", ""),
      )
    table_data.append([_truncate(cell, truncate) for cell in row])
  print(tabulate(table_data, headers=headers))


def _get_emoji_by_status(status: str) -> str:
  emoji_by_status = {
      "queued": "⌛",
      "running": "🏃",
      "completed": "✅",
      # An extra space is added because this emoji eats a space from the right.
      "cancelled": "⏹️ ",
      "failed": "❌",
  }
  return emoji_by_status.get(status.lower().strip(), " ")


def _truncate(text: str, max_length: int | None = None) -> str:
  text = str(text)
  if max_length and len(text) > max_length:
    return text[:max_length - 3] + "..."
  return text
