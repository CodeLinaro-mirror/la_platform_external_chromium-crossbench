# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import logging
import os
import zipfile
from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench.plt.base import SubprocessError
from crossbench.probes.profiling.system_profiling import ProfilingProbe
from crossbench.probes.trace_processor.context.base import \
    TraceProcessorProbeContext

if TYPE_CHECKING:
  from crossbench import path as pth
  from crossbench.probes.results import LocalProbeResult

KB = 1024

class TraceProcessorSymbolizingProbeContext(TraceProcessorProbeContext):

  @property
  def should_symbolize_profile(self) -> bool:
    if not self.probe.symbolize_profile:
      return False
    return self.run.has_probe_context(ProfilingProbe)

  @override
  def _merge_trace_files(self) -> LocalProbeResult:
    result = super()._merge_trace_files()
    if self.should_symbolize_profile:
      return self._symbolize_profile(result)
    return result

  def _symbolize_profile(self, result: LocalProbeResult) -> LocalProbeResult:
    llvm_symbolizer_bin = self.probe.llvm_symbolizer_bin
    if not llvm_symbolizer_bin:
      logging.error("Could not find llvm-symbolizer binary")
      return result
    traceconv_bin = self.probe.traceconv_bin
    if not traceconv_bin:
      logging.error("Could not find traceconv binary")
      return result

    merged_file = result.get("zip")
    symbols_result = self.local_result_path / "symbols.pb"
    env = {
        "PERFETTO_SYMBOLIZER_MODE": "index",
        "PERFETTO_BINARY_PATH": str(self.run.browser.app_path.parent),
        **self.host_platform.environ,
    }
    env["PATH"] = (os.pathsep).join(
        (str(llvm_symbolizer_bin.parent), env.get("PATH", "")))
    try:
      self.host_platform.sh(
          traceconv_bin, "symbolize", merged_file, symbols_result, env=env)
    except SubprocessError as e:
      logging.error("Symbolization failed: %s", e)

    if not self.host_platform.exists(symbols_result) or (
        self.host_platform.file_size(symbols_result) < 100 * KB):
      # Figure out why this regularly fails
      logging.error("Could not generate valid symbols file: %s", symbols_result)
      return result

    return self._maybe_symbolized_result(result, symbols_result)

  def _maybe_symbolized_result(
      self, result: LocalProbeResult,
      symbols_result: pth.LocalPath) -> LocalProbeResult:
    with zipfile.ZipFile(self._symbolized_trace_path, "w") as zip_file:
      for f in (*result.perfetto_list, symbols_result):
        zip_file.write(f, arcname=f.relative_to(self.run.out_dir))

    if (self.host_platform.file_size(self._symbolized_trace_path)
        < self.host_platform.file_size(self.merged_trace_path)):
      logging.error("Failed to generated symbolized trace file")
      return result

    # If we have a successfully symbolized trace file we can replace
    # the original merged_trace.zip.
    self.host_platform.rm(self.merged_trace_path)
    self.host_platform.rename(self._symbolized_trace_path,
                              self.merged_trace_path)
    return self.local_result(perfetto=(self.merged_trace_path,))
