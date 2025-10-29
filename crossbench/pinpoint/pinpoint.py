# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

from typing import TYPE_CHECKING

from crossbench.pinpoint.list_jobs import list_jobs

if TYPE_CHECKING:
  import argparse


def run(args: argparse.Namespace) -> None:
  """Runs Pinpoint CLI with the provided arguments."""
  if args.action == "list":
    list_jobs(args.user, args.number, args.truncate)
