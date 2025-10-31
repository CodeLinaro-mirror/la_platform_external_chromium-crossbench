# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import csv
import datetime
import itertools
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

import requests
import yaml
from tabulate import tabulate

from crossbench.pinpoint.api import JOB_SHORTEN_URL_TEMPLATE, \
    PINPOINT_JOBS_API_URL, USERINFO_API_URL
from crossbench.pinpoint.auth import get_auth_session
from crossbench.pinpoint.list_format import ListFormatEnum
from crossbench.pinpoint.user import UserEnum

if TYPE_CHECKING:
  from google.auth.transport import requests as auth_requests


def list_jobs(user: UserEnum | str, number: int, truncate: int | None,
              output_format: ListFormatEnum) -> None:
  authed_session = get_auth_session()

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

    _display_jobs(jobs[:number], output_format, user == UserEnum.ALL, truncate)

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


def _get_user_email(authed_session: auth_requests.AuthorizedSession) -> str:
  response = authed_session.get(USERINFO_API_URL)
  response.raise_for_status()
  return response.json()["email"]


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


def _prepare_job_list_data(
    jobs: list[dict[str, Any]],
    all_users: bool) -> tuple[list[str], list[list[Any]]]:
  headers = [
      "Job URL", "Benchmark", "Configuration", "Type", "Created Time", "Status"
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
        job.get("arguments", {}).get("benchmark", ""),
        job.get("configuration", ""),
        job.get("comparison_mode", ""),
        created_time,
        status,
    ]
    if all_users:
      row.insert(
          4,
          job.get("user", ""),
      )
    table_data.append(row)
  return headers, table_data


def _display_jobs(jobs: list[dict[str, Any]], output_format: ListFormatEnum,
                  all_users: bool, truncate: int | None) -> None:
  match output_format:
    case ListFormatEnum.JSON:
      print(json.dumps(jobs, indent=2))
    case ListFormatEnum.YAML:
      print(yaml.dump(jobs))
    case ListFormatEnum.CSV:
      headers, rows = _prepare_job_list_data(jobs, all_users)
      writer = csv.writer(sys.stdout)
      writer.writerow(headers)
      writer.writerows(rows)
    case ListFormatEnum.TSV:
      headers, rows = _prepare_job_list_data(jobs, all_users)
      writer = csv.writer(sys.stdout, delimiter="\t")
      writer.writerow(headers)
      writer.writerows(rows)
    case ListFormatEnum.TABLE:
      headers, rows = _prepare_job_list_data(jobs, all_users)
      _display_jobs_as_table(headers, rows, truncate)


def _display_jobs_as_table(headers: list[str], rows: list,
                           truncate: int | None) -> None:
  table_data = [[_truncate(cell, truncate) for cell in row] for row in rows]
  for row in table_data:
    row[-1] = _get_emoji_by_status(row[-1]) + row[-1]
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
