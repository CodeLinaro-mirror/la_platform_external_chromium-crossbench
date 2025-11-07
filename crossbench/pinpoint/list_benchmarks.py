# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from crossbench.pinpoint.api import CHROMEPERF_TEST_SUITES_API_URL
from crossbench.pinpoint.auth import get_auth_session
from crossbench.pinpoint.helper import annotate


def fetch_benchmarks() -> list[str]:
  """Fetches the list of available benchmarks from the Chromeperf API."""
  authed_session = get_auth_session()
  with annotate("Fetching benchmarks"):
    response = authed_session.post(CHROMEPERF_TEST_SUITES_API_URL)
    response.raise_for_status()
    return response.json()


def print_benchmarks() -> None:
  """Prints the list of available Pinpoint benchmarks."""
  benchmarks = fetch_benchmarks()
  print("\n".join(benchmarks))
