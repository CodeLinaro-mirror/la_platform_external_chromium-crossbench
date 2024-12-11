# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import subprocess
from typing import TYPE_CHECKING, Optional

from crossbench.probes.probe_context import ProbeContext
from crossbench.probes.v8.log import V8LogProbe

if TYPE_CHECKING:
  from crossbench.probes.profiling.system_profiling import ProfilingProbe
  from crossbench.runner.run import Run


class ProfilingContext(ProbeContext, metaclass=abc.ABCMeta):

  def __init__(self, probe: ProfilingProbe, run: Run) -> None:
    super().__init__(probe, run)
    self._profiling_process: Optional[subprocess.Popen] = None

  def setup_v8_log_path(self) -> None:
    if any(isinstance(probe, V8LogProbe) for probe in self.run.probes):
      return
    # Try to get a bit a cleaner output folder by redirecting v8 logging output
    # to v8.log.
    v8_log_dir = self.result_path.parent / V8LogProbe.NAME / "v8.log"
    self.browser_platform.mkdir(v8_log_dir)
    self.session.extra_js_flags["--logfile"] = str(v8_log_dir)
