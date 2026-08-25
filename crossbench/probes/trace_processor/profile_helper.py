# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from crossbench.probes.trace_processor.trace_processor import \
    TraceProcessorProbe

if TYPE_CHECKING:
  from crossbench.probes.probe import Probe
  from crossbench.runner.runner import Runner


def get_extra_trace_processor(runner: Runner) -> Iterable[Probe]:
  if (runner.has_probe("perfetto") and runner.has_probe("profiling") and
      not runner.has_probe(TraceProcessorProbe.NAME)):
    # Install an additional TraceProcessorProbe to symbolize complex
    # traces with profiles data.
    return (TraceProcessorProbe(),)
  return ()
