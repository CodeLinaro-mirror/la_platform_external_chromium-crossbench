# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from asyncio.subprocess import Process
from subprocess import Popen
from typing import IO, NotRequired, Sequence, TypedDict

from crossbench import path as pth

type CmdArg = pth.AnyPathLike
type SequenceCmdArgs = Sequence[CmdArg]
type ListCmdArgs = list[CmdArg]
type TupleCmdArgs = tuple[CmdArg, ...]
type CmdArgs = ListCmdArgs | TupleCmdArgs

type ProcessLike = Popen | Process | int

type ProcessIo = int | IO[str] | IO[bytes] | None

type PlatformKey = tuple[str, ...]


class ProcessInfo(TypedDict):
  pid: int
  name: NotRequired[str]
  exe: NotRequired[str | None]
  cmdline: NotRequired[list[str] | None]
  status: NotRequired[str]
  comm: NotRequired[str]
