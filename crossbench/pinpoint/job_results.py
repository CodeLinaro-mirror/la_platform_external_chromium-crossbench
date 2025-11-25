# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
from typing import Any
from urllib.parse import urlparse

from google.cloud import storage
from typing_extensions import override

from crossbench import path as pth
from crossbench import plt
from crossbench.env.base import BaseEnv
from crossbench.pinpoint.helper import annotate
from crossbench.pinpoint.job_config import fetch_job_config
from crossbench.runner.runner import Runner


class PinpointJobResults:

  def __init__(self, data: dict[str, Any]) -> None:
    self.data = data
    with annotate("Parsing job results"):
      if self.status.lower() != "completed":
        raise ValueError(f"Job is not completed. Status: {self.status}")

      self.name = f"pinpoint_{self.benchmark}_{self.bot}"
      self.results_url = data.get("results_url")
      self.variants = [
          PinpointVeriantResults(v, i)
          for i, v in enumerate(data.get("state", []))
      ]
      self.attempts_count = sum(len(v.attempts) for v in self.variants)

  @property
  def arguments(self) -> dict[str, Any]:
    return self.data.get("arguments", {})

  @property
  def benchmark(self) -> str:
    return self.arguments.get("benchmark", "")

  @property
  def bot(self) -> str:
    return self.arguments.get("configuration", "")

  @property
  def status(self) -> str:
    return self.data["status"]


class PinpointVeriantResults:

  def __init__(self, data: dict[str, Any], index: int) -> None:
    self.data = data
    self.index = index
    self.name = self.form_variant_name()
    self.attempts = [
        PinpointAttemptResults(attempt, index)
        for index, attempt in enumerate(data.get("attempts", []))
    ]

  @property
  def change(self) -> dict[str, Any]:
    return self.data.get("change", {})

  def form_variant_name(self) -> str:
    if label := self.change.get("label"):
      return label

    parts = []
    for commit in self.change.get("commits", []):
      parts.append(commit.get("repository"))
      parts.append(commit.get("commit_position"))

    parts = [str(part) for part in parts if part]
    if parts:
      return "_".join(parts)

    return f"variant_{self.index}"


class PinpointAttemptResults:

  def __init__(self, data: dict[str, Any], index: int) -> None:
    self.data = data
    self.index = index
    self.cas_isolate = self.find_results_isolate()
    self.perfetto_traces_url = self.find_perfetto_traces_url()

  @property
  def executions(self) -> list[dict[str, Any]]:
    return self.data.get("executions", [])

  def find_results_isolate(self) -> str | None:
    if len(self.executions) < 2:
      return None

    for details in self.executions[1].get("details", []):
      if details.get("key") == "isolate" and details.get("value"):
        return details.get("value")

    return None

  def find_perfetto_traces_url(self) -> str | None:
    if len(self.executions) < 3:
      return None

    for details in self.executions[2].get("details", []):
      if details.get("key") == "trace" and details.get("url"):
        return details.get("url")

    return None


class Environment(BaseEnv):

  @override
  def validate(self) -> None:
    pass


def download_results(job_id: str, out_dir: pth.LocalPath | None = None) -> None:
  """Downloads results of a Pinpoint job."""
  Environment(plt.PLATFORM).check_installed(["cas"])
  job_results = PinpointJobResults(fetch_job_config(job_id, full=True))

  out_dir = out_dir or Runner.get_out_dir(
      pathlib.Path.cwd(), suffix=job_results.name)
  out_dir.mkdir(parents=True, exist_ok=True)

  if job_results.results_url:
    with annotate("Downloading HTML results"):
      _download_from_storage(job_results.results_url, out_dir)

  current_attempt = 0
  for variant in job_results.variants:
    variant_dir = out_dir / variant.name
    for attempt in variant.attempts:
      progress = 100 * current_attempt / job_results.attempts_count
      current_attempt += 1
      with annotate(f"Downloading results {progress:.1f}%"):
        attempt_dir = variant_dir / str(attempt.index + 1)
        attempt_dir.mkdir(parents=True, exist_ok=True)

        if attempt.cas_isolate:
          _download_cas_isolate(attempt.cas_isolate, attempt_dir)
        if attempt.perfetto_traces_url:
          _download_from_storage(attempt.perfetto_traces_url, attempt_dir)


def _download_cas_isolate(isolate: str, out_dir: pth.LocalPath) -> None:
  cmd = [
      "cas", "download", "-cas-instance",
      "projects/chrome-swarming/instances/default_instance", "-digest", isolate,
      "-dir",
      str(out_dir)
  ]
  plt.PLATFORM.sh(*cmd)


def _download_from_storage(url: str, out_dir: pth.LocalPath) -> None:
  parsed_url = urlparse(url)
  path_segments = parsed_url.path.strip("/").split("/", 1)
  if len(path_segments) < 2:
    raise ValueError(f"Invalid GCS URL: {url}")

  bucket_name = path_segments[0]
  blob_name = path_segments[1]

  filename = blob_name.split("/")[-1]
  output_file = out_dir / filename

  client = storage.Client()
  bucket = client.bucket(bucket_name)
  blob = bucket.blob(blob_name)

  blob.download_to_filename(str(output_file))
