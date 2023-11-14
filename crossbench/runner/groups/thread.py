# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import logging
import threading
from typing import Iterable, Tuple, TYPE_CHECKING

from ordered_set import OrderedSet

if TYPE_CHECKING:
  from crossbench.runner.run import Run
  from crossbench.runner.runner import Runner
  from .session import BrowserSessionRunGroup


class RunThreadGroup(threading.Thread):
  """The main interface to start Runs.
  - Typically only a single RunThreadGroup is used.
  - If runs are executed in parallel, multiple RunThreadGroup are used
  """

  def __init__(self, runs: Iterable[Run]) -> None:
    super().__init__()
    self._runs = tuple(runs)
    self._browser_sessions: OrderedSet[BrowserSessionRunGroup] = OrderedSet(
        run.browser_session for run in runs)
    assert self._runs, "Got unexpected empty runs list"
    self._runner: Runner = self._runs[0].runner
    self.is_dry_run: bool = False
    self._verify_contains_all_browser_session_runs()

  def _verify_contains_all_browser_session_runs(self) -> None:
    runs_set = set(self._runs)
    for browser_session in self._browser_sessions:
      for session_run in browser_session.runs:
        assert session_run in runs_set, (
            f"BrowserSession {browser_session} is not allowed to have "
            f"{session_run} in another RunThreadGroup.")

  @property
  def runs(self) -> Tuple[Run, ...]:
    return tuple(self._runs)

  def run(self) -> None:
    total_run_count = len(self._runner.runs)
    for browser_session in self._browser_sessions:
      with browser_session.open():
        for run in browser_session.runs:
          logging.info("=" * 80)
          logging.info("RUN %s/%s", run.index + 1, total_run_count)
          logging.info("=" * 80)
          run.run(self.is_dry_run)
          if run.is_success:
            run.log_results()
          else:
            self._runner.exceptions.extend(run.exceptions)
