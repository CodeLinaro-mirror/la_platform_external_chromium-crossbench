# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Iterable, Iterator, List, Optional

from crossbench import compat
from crossbench.probes.results import EmptyProbeResult

from .base import RunGroup

if TYPE_CHECKING:
  import pathlib

  from crossbench import exception, plt
  from crossbench.browsers.browser import Browser
  from crossbench.probes.probe import Probe
  from crossbench.probes.results import ProbeResult
  from crossbench.runner.run import Run
  from crossbench.runner.runner import Runner
  from crossbench.types import JsonDict


class BrowserSessionRunGroup(RunGroup):
  """
  Groups Run objects together that are run within the same browser session.
  At the beginning of a new session the caches are cleared and the
  browser is (re-)started.
  """

  class State(compat.StrEnum):
    BUILDING = "building"
    READY = "ready"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    DONE = "done"

  def __init__(self, browser: Browser, index: int, root_dir: pathlib.Path,
               throw: bool) -> None:
    super().__init__(throw)
    self._state = self.State.BUILDING
    self._browser = browser
    self._index = index
    self._runs: List[Run] = []
    self._root_dir: pathlib.Path = root_dir
    self._browser_tmp_dir: Optional[pathlib.Path] = None

  def append(self, run: Run) -> None:
    assert self._state == self.State.BUILDING
    assert run.browser_session == self
    assert run.browser is self._browser
    # TODO: assert that the runs have compatible flags (likely we're only
    # allowing changes in the cache temperature)
    # TODO: Add session/run switch for probe results
    self._runs.append(run)

  def set_ready(self) -> None:
    assert self._state == self.State.BUILDING
    self._state = self.State.READY
    self._validate()
    self._set_path(self._get_session_dir())

  def _validate(self) -> None:
    if not self._runs:
      raise ValueError("BrowserSessionRunGroup must be non-empty.")
    self._validate_same_browser_probes()

  def _validate_same_browser_probes(self) -> None:
    first_run = self._runs[0]
    first_probes = tuple(first_run.probes)
    for index, run in enumerate(self.runs):
      if first_run.browser is not run.browser:
        raise ValueError("A browser session can only contain "
                         "Runs with the same Browser.\n"
                         f"runs[0].browser == {first_run.browser} vs. "
                         f"runs[{index}].browser == {run.browser}")
      if first_probes != tuple(run.probes):
        raise ValueError("Got conflicting Probes within a browser session.")

  @property
  def raw_sessions_dir(self) -> pathlib.Path:
    return (self.root_dir / self.browser.unique_name / "sessions" /
            str(self.index))

  @property
  def is_single_run(self) -> bool:
    return len(self._runs) == 1

  def _get_session_dir(self) -> pathlib.Path:
    if self.is_single_run:
      return self._runs[0].out_dir
    return self.raw_sessions_dir

  @property
  def browser(self) -> Browser:
    return self._browser

  @property
  def index(self) -> int:
    return self._index

  @property
  def browser_platform(self) -> plt.Platform:
    return self._browser.platform

  @property
  def is_running(self) -> bool:
    return self._state == self.State.RUNNING

  @property
  def is_remote(self) -> bool:
    return self.browser_platform.is_remote

  @property
  def root_dir(self) -> pathlib.Path:
    return self._root_dir

  @property
  def runs(self) -> Iterable[Run]:
    return iter(self._runs)

  @property
  def info_stack(self) -> exception.TInfoStack:
    return ("Merging results from multiple browser sessions",
            f"browser={self.browser.unique_name}", f"session={self.index}")

  @property
  def info(self) -> JsonDict:
    info_dict = super().info
    info_dict.update({"index": self.index})
    return info_dict

  @property
  def browser_tmp_dir(self) -> pathlib.Path:
    if not self._browser_tmp_dir:
      prefix = f"cb_browser_session_{self.index}"
      self._browser_tmp_dir = self.browser_platform.mkdtemp(prefix)
    return self._browser_tmp_dir

  def merge(self, runner: Runner) -> None:
    # TODO: implement merging of session probes
    pass

  def _merge_probe_results(self, probe: Probe) -> ProbeResult:
    return EmptyProbeResult()

  @contextlib.contextmanager
  def open(self) -> Iterator[BrowserSessionRunGroup]:
    self._setup()
    try:
      yield self
    finally:
      self._teardown()

  def _setup(self) -> None:
    assert self._state == self.State.READY
    self._state = self.State.STARTING
    self._setup_session_dir()
    self._start_browser()
    # TODO: figure ouy when this is created the first time
    self.path.mkdir(parents=True, exist_ok=True)
    self._state = self.State.RUNNING

  def _setup_session_dir(self):
    self.path.mkdir(parents=True, exist_ok=True)
    if self.is_single_run:
      # If there is a single run per session we reuse the run-dir.
      self.raw_sessions_dir.parent.mkdir(parents=True, exist_ok=True)
      self.raw_sessions_dir.symlink_to(self.path)

  def _start_browser(self) -> None:
    assert self._state == self.State.STARTING
    # TODO: implement

  def _teardown(self) -> None:
    assert self._state == self.State.RUNNING
    self._state = self.State.STOPPING
    try:
      self._stop_browser()
    finally:
      assert self._state == self.State.STOPPING
      self._state = self.State.DONE

  def _stop_browser(self) -> None:
    assert self._state == self.State.STOPPING
    # TODO: implement

  # TODO: remove once cleanly implemented
  def is_first_run(self, run: Run) -> bool:
    return self._runs[0] is run

  # TODO: remove once cleanly implemented
  def is_last_run(self, run: Run) -> bool:
    return self._runs[-1] is run
