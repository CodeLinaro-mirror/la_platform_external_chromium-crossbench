# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import logging
from subprocess import TimeoutExpired
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
  import signal
  from subprocess import Popen


def wait_and_kill(process: Popen,
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


def wait_and_terminate(process,
                       timeout=1,
                       signal: Optional[signal.Signals] = None) -> None:
  if process.poll() is not None:
    return
  logging.debug("Terminating process: %s", process)
  try:
    if signal:
      process.send_signal(signal)
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
