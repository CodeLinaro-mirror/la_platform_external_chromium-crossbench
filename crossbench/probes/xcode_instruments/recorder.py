# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import atexit
import logging
import subprocess
import threading
from typing import IO, TYPE_CHECKING, Final

from crossbench.cli.ui import ui
from crossbench.helper.wait import WaitRange, wait_with_backoff

if TYPE_CHECKING:
  from crossbench import path as pth
  from crossbench.plt.macos import MacOSPlatform

_START_TIMEOUT_S: Final[int] = 30
_DEFAULT_STOP_TIMEOUT_S: Final[int] = 3 * 60
_OUTPUT_THREAD_JOIN_TIMEOUT_S: Final[int] = 5
# Printed by `xctrace record` once it is actually capturing events. The trace
# bundle is created a few seconds earlier, so its existence is not enough.
_RECORDING_STARTED_MARKER: Final[str] = "Ctrl-C to stop the recording"


class XctraceRecorder:
  """Drives an `xctrace record` subprocess."""

  def __init__(self,
               host_platform: MacOSPlatform,
               template: pth.AnyPath,
               output_path: pth.AnyPath,
               attach_pid: int | None = None,
               device_udid: str | None = None,
               stop_timeout_s: int = _DEFAULT_STOP_TIMEOUT_S) -> None:
    """Initialize an XctraceRecorder.

    Args:
      host_platform: Host platform to execute `xctrace` on.
      template: Path to the `.tracetemplate` to record with.
      output_path: Destination path for the `.trace` bundle.
      attach_pid: Optional PID to attach to. If None (default), records all
        processes on the target device (`--all-processes`).
      device_udid: Optional device UDID for recording a connected iOS device.
      stop_timeout_s: Maximum seconds to wait for xctrace to stop and finalize.
    """
    self._host_platform: Final[MacOSPlatform] = host_platform
    self._template: Final[pth.AnyPath] = template
    self._output_path: Final[pth.AnyPath] = output_path
    self._attach_pid: Final[int | None] = attach_pid
    self._device_udid: Final[str | None] = device_udid
    self._stop_timeout_s: Final[int] = stop_timeout_s
    self._process: subprocess.Popen | None = None
    self._output_thread: threading.Thread | None = None
    self._recording_started: Final[threading.Event] = threading.Event()

  @property
  def is_recording(self) -> bool:
    return self._process is not None

  def start(self) -> None:
    assert self._host_platform.is_file(
        self._template), f"Didn't find trace template {self._template}"
    # Finalize even if the run is interrupted, so the trace is not corrupted.
    atexit.register(self.finalize)

    process_filter = (["--attach", str(self._attach_pid)]
                      if self._attach_pid is not None else ["--all-processes"])
    device_args = (["--device", self._device_udid] if self._device_udid else [])
    self._recording_started.clear()
    self._process = self._host_platform.popen(
        "xctrace",
        "record",
        "--template",
        self._template,
        *device_args,
        *process_filter,
        "--output",
        self._output_path,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8")
    assert self._process.stdout, "Missing xctrace stdout pipe"
    self._output_thread = threading.Thread(
        target=self._read_output, args=(self._process.stdout,), daemon=True)
    self._output_thread.start()
    self._wait_for_recording_started()

  def _read_output(self, stdout: IO[str]) -> None:
    """Forwards xctrace's output to the log and detects the recording start.

    Runs on a background thread, which also keeps the pipe drained.
    """
    for line in stdout:
      logging.info("xctrace: %s", line.rstrip())
      if _RECORDING_STARTED_MARKER in line:
        self._recording_started.set()

  def _wait_for_recording_started(self) -> None:
    assert self._process
    try:
      for _ in wait_with_backoff(WaitRange(timeout=_START_TIMEOUT_S)):
        if self._recording_started.is_set():
          return
        if self._process.poll() is not None:
          raise ValueError("Could not start xctrace record")
    except TimeoutError:
      logging.warning("xctrace took too long to start recording. "
                      "Samples might be missing.")

  def request_stop(self) -> None:
    """Signals `xctrace` to stop recording without blocking.

    Sends `SIGINT` to the `xctrace` subprocess so it stops capturing events
    and begins flushing trace data to disk in the background. Does not wait
    for the trace file to be fully written.
    """
    assert self._process, "Recording was not started"
    self._host_platform.send_signal(self._process,
                                    self._host_platform.signals.SIGINT)

  def finalize(self) -> None:
    """Waits for `xctrace` to finish writing the trace bundle to disk.

    Blocks until the `xctrace` process terminates gracefully (up to
    `stop_timeout_s`), sending `SIGINT` first if `stop()` was not called yet.
    Then verifies that the trace bundle was properly written.
    """
    if not self._process:
      return
    logging.info("  Waiting for xctrace to finalize the trace (slow)...")
    with ui.spinner():
      self._host_platform.terminate_gracefully(
          self._process,
          signal=self._host_platform.signals.SIGINT,
          timeout=self._stop_timeout_s)
    success_file = self._output_path / "open.creq"
    if not self._host_platform.exists(success_file):
      logging.error("xctrace failed to flush cleanly. "
                    "The trace bundle might be corrupted or empty.")
    self._process = None
    if self._output_thread:
      self._output_thread.join(timeout=_OUTPUT_THREAD_JOIN_TIMEOUT_S)
      self._output_thread = None
    atexit.unregister(self.finalize)
