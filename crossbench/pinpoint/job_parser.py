# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import re
from typing import Sequence


def parse_job_id(value: str) -> str:
  value = value.strip().lower()
  parts = [p for p in value.split("/") if p]
  if not parts or not re.fullmatch(r"[0-9a-f]+", parts[-1]):
    raise argparse.ArgumentTypeError(f"Invalid job ID: {value}")
  return parts[-1]


def parse_job_ids(values: Sequence[str]) -> list[str]:
  job_ids: list[str] = []
  for item in values:
    for part in item.split(","):
      part = part.strip()
      if part:
        job_ids.append(parse_job_id(part))
  if not job_ids:
    raise argparse.ArgumentTypeError("No valid job IDs provided.")
  return job_ids
