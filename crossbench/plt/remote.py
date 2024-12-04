# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import subprocess
from signal import Signals
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
  from crossbench.path import AnyPathLike, LocalPath
  from crossbench.plt.base import CmdArg, ListCmdArgs, Platform


class RemotePlatformMixin:

  def __init__(self, host_platform: Platform):
    super().__init__()
    self._host_platform: Platform = host_platform

  @property
  def is_remote(self) -> bool:
    return True

  @property
  def host_platform(self) -> Platform:
    return self._host_platform

  def host_path(self, path: AnyPathLike) -> LocalPath:
    return self._host_platform.local_path(path)

  def build_shell_cmd(self, *args: CmdArg) -> ListCmdArgs:
    raise NotImplementedError()


class RemotePopen(subprocess.Popen):
  """
  A wrapper class to represent a process running on a remote platform.

  Allows to send signals to the remote process and gracefully wait for its
  termination.
  """

  def __init__(self,
               platform: Platform,
               args: ListCmdArgs,
               bufsize=-1,
               stdout=None,
               stderr=None,
               stdin=None):
    self._platform: Platform = platform
    self._pid: Optional[int] = None
    super().__init__(
        args, bufsize=bufsize, stdout=stdout, stderr=stderr, stdin=stdin)

  def set_pid(self, pid: int) -> None:
    assert self._pid is None, "Should not set PID twice"
    self._pid = pid

  def send_signal(self, signal: Union[int, Signals]) -> None:
    assert self._pid
    self._platform.send_signal(self._pid, Signals(signal))

  def terminate(self) -> None:
    assert self._pid
    self._platform.terminate(self._pid)

  def kill(self) -> None:
    assert self._pid
    self._platform.kill(self._pid)
