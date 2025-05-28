# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import sys
import threading
import time
from typing import Final, Iterable

CLEAR_END: Final[str] = "\x1b[J"
STORE_CURSOR_POS: Final[str] = "\x1b[s"
RESTORE_CURSOR_POS: Final[str] = "\x1b[u"

class Spinner:
  CURSORS = "◐◓◑◒"

  def __init__(self, sleep: float = 0.5, title: str = "") -> None:
    self._is_running: bool = False
    self._sleep_time_seconds: float = sleep
    self._title: str = title
    self._message: str = ""
    self._cursor: str = " "

  def __enter__(self) -> None:
    # Only enable the spinner if the output is an interactive terminal.
    is_atty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    if is_atty:
      self._is_running = True
      threading.Thread(target=self._spin).start()

  def __exit__(self, exc_type, exc_value, traceback) -> None:
    if self._is_running:
      self._is_running = False
      self._sleep()

  def _cursors(self) -> Iterable[str]:
    while True:
      yield from Spinner.CURSORS

  def _spin(self) -> None:
    for cursor in self._cursors():
      self._cursor = cursor
      if not self._is_running:
        return
      self._write_message()
      self._sleep()

  def _sleep(self) -> None:
    time.sleep(self._sleep_time_seconds)

  def write(self, message: str) -> None:
    self._message = message
    self._write_message()

  @property
  def title(self) -> str:
    return self._title

  @title.setter
  def title(self, title: str) -> None:
    self._title = title
    self._write_message()

  def _write_message(self) -> None:
    stdout = sys.stdout
    stdout.write(f"{STORE_CURSOR_POS} {self._cursor} "
                 f"{self._title}{self._message}{CLEAR_END}{RESTORE_CURSOR_POS}")
    stdout.flush()
