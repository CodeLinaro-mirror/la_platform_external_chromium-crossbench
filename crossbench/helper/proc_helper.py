# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import logging
from subprocess import Popen, TimeoutExpired
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
  import signal
  from asyncio.subprocess import Process
  KillableProcess = Union[Popen, Process]


def wait_and_kill(process: KillableProcess,
                  timeout=1,
                  signal: Optional[signal.Signals] = None) -> None:
  """Graceful process termination:
  1. Send signal if provided,
  2. wait for the given time,
  3. terminate(),
  4. Last stage: kill process.
  """
  logging.debug("wait_and_kill: %s", process)
  try:
    wait_and_terminate(process, timeout, signal)
  finally:
    try:
      process.kill()
    except ProcessLookupError:
      pass


def wait_and_terminate(process: KillableProcess,
                       timeout=1,
                       signal: Optional[signal.Signals] = None) -> None:
  if isinstance(process, Popen) and process.poll() is not None:
    return
  logging.debug("Terminating process: %s", process)
  try:
    if signal:
      process.send_signal(signal)
    if isinstance(process, Popen):
      process.wait(timeout)
    return
  except TimeoutExpired as e:
    logging.debug("Got timeout while waiting "
                  "for process shutdown (%s): %s", process, e)
  except Exception as e:  # pylint: disable=broad-except
    logging.debug("Ignoring exception during process termination: %s", e)
  finally:
    try:
      process.terminate()
    except ProcessLookupError:
      pass
