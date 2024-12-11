# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import atexit
import logging
import signal
import subprocess
import time
from typing import TYPE_CHECKING, Final, Optional

import crossbench.path as pth
from crossbench.helper import proc_helper
from crossbench.helper.spinner import Spinner
from crossbench.probes.profiling.context.base import ProfilingContext

if TYPE_CHECKING:
  from crossbench.probes.results import ProbeResult

_MAC_TRACE_TEMPLATE_PATH: Final[pth.LocalPath] = pth.LocalPath(
    __file__).parents[1] / "time-profile.tracetemplate"


class MacOSProfilingContext(ProfilingContext):
  _process: Optional[subprocess.Popen]

  def get_default_result_path(self) -> pth.AnyPath:
    return super().get_default_result_path().parent / "profile.trace"

  def start(self) -> None:
    assert self.browser_platform.is_file(_MAC_TRACE_TEMPLATE_PATH), (
        f"Didn't find {_MAC_TRACE_TEMPLATE_PATH}")
    self._process = self.browser_platform.popen("xctrace", "record",
                                                "--template",
                                                _MAC_TRACE_TEMPLATE_PATH,
                                                "--all-processes", "--output",
                                                self.result_path)
    # xctrace takes some time to start up
    time.sleep(3)
    if self._process.poll():
      raise ValueError("Could not start xctrace")
    atexit.register(self.stop_process)

  def stop(self) -> None:
    # Needs to be SIGINT for xctrace, terminate won't work.
    assert self._process
    self._process.send_signal(signal.SIGINT)

  def teardown(self) -> ProbeResult:
    self.stop_process()
    return self.browser_result(file=(self.result_path,))

  def stop_process(self) -> None:
    if self._process:
      logging.info("  Waiting for xctrace profiles (slow)...")
      with Spinner():
        proc_helper.wait_and_kill(
            self._process, signal=signal.SIGINT, timeout=60)
      self._process = None
    atexit.unregister(self.stop_process)
