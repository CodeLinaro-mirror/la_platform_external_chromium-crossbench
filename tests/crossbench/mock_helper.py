# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import collections
import datetime as dt
import pathlib
import shlex
import subprocess
from typing import (TYPE_CHECKING, Any, Dict, Iterable, List, Mapping, Optional,
                    Sequence, Union)

import psutil

from crossbench import path as pth
from crossbench import plt
from crossbench.benchmarks.base import SubStoryBenchmark
from crossbench.cli.cli import CrossBenchCLI
from crossbench.plt.android_adb import Adb, AndroidAdbPlatform
from crossbench.plt.base import MachineArch, Platform
from crossbench.plt.chromeos_ssh import ChromeOsSshPlatform
from crossbench.plt.linux import LinuxPlatform
from crossbench.plt.linux_ssh import LinuxSshPlatform
from crossbench.plt.macos import MacOSPlatform
from crossbench.plt.win import WinPlatform
from crossbench.runner.run import Run
from crossbench.stories.story import Story

if TYPE_CHECKING:
  from crossbench.plt.base import ListCmdArgs, TupleCmdArgs
  from crossbench.runner.runner import Runner


GIB = 1014**3



class MockPlatformMixin:

  def __init__(self, *args, is_battery_powered=False, **kwargs):
    self._is_battery_powered = is_battery_powered
    # Cache some helper properties that might fail under pyfakefs.
    self._sh_cmds: List[TupleCmdArgs] = []
    self._expected_sh_cmds: Optional[List[TupleCmdArgs]] = None
    self._sh_results: List[bytes] = []
    self.file_contents: Dict[pth.AnyPath, List[str]] = (
        collections.defaultdict(list))
    self.sleeps: List[dt.timedelta] = []
    self.popens: List[MockPopen] = []
    self.mkdir_calls: int = 0
    super().__init__(*args, **kwargs)

  def expect_sh(self,
                *args: Union[str, pathlib.Path],
                result: Union[str, bytes] = "") -> None:
    if args:
      if self._expected_sh_cmds is None:
        self._expected_sh_cmds = []
      self._expected_sh_cmds.append(self._convert_sh_args(*args))
    if isinstance(result, str):
      result = result.encode("utf-8")
    assert isinstance(result, bytes)
    self._sh_results.append(result)

  def _convert_sh_args(self, *args: Union[str, pathlib.Path]) -> TupleCmdArgs:
    converted_args : ListCmdArgs = []
    for arg in args:
      if not isinstance(arg, (str, pathlib.PurePath)):
        arg = str(arg)
      converted_args.append(arg)
    return tuple(converted_args)

  @property
  def sh_results(self) -> List[bytes]:
    return list(self._sh_results)

  @sh_results.setter
  def sh_results(self, results: Iterable[Union[str, bytes]]) -> None:
    assert not self._sh_results, "Trying to override non-consumed results"
    assert not self._expected_sh_cmds, (
        "expect_sh() cannot be used together with sh_results")
    for result in results:
      self.expect_sh(result=result)

  @property
  def sh_cmds(self) -> List[TupleCmdArgs]:
    return list(self._sh_cmds)

  @property
  def expected_sh_cmds(self) -> Optional[List[TupleCmdArgs]]:
    if self._expected_sh_cmds is None:
      return None
    return list(self._expected_sh_cmds)

  @property
  def name(self) -> str:
    return f"mock.{super().name}"

  @property
  def machine(self) -> MachineArch:
    return MachineArch.ARM_64

  @property
  def version(self) -> str:
    return "1.2.3.4.5"

  @property
  def device(self) -> str:
    return "TestBook Pro"

  @property
  def cpu(self) -> str:
    return "Mega CPU @ 3.00GHz"

  @property
  def is_battery_powered(self) -> bool:
    return self._is_battery_powered

  def is_thermal_throttled(self) -> bool:
    return False

  def disk_usage(self, path: pathlib.Path):
    del path
    # pylint: disable=protected-access
    return psutil._common.sdiskusage(
        total=GIB * 100, used=20 * GIB, free=80 * GIB, percent=20)

  def cpu_usage(self) -> float:
    return 0.1

  def cpu_details(self) -> Dict[str, Any]:
    return {"physical cores": 2, "logical cores": 4, "info": self.cpu}

  def set_file_contents(self,
                        file: pth.AnyPathLike,
                        data: str,
                        encoding: str = "utf-8") -> None:
    del encoding
    file_path = self.path(file)
    self.file_contents[file_path].append(data)

  def system_details(self):
    return {"CPU": "20-core 3.1 GHz"}

  def sleep(self, duration):
    self.sleeps.append(duration)

  def processes(self, attrs=()):
    del attrs
    return []

  def process_children(self, parent_pid: int, recursive=False):
    del parent_pid, recursive
    return []

  def foreground_process(self):
    return None

  def search_platform_binary(
      self,
      name: str,
      macos: Sequence[str] = (),
      win: Sequence[str] = (),
      linux: Sequence[str] = ()
  ) -> pth.AnyPath:
    del macos, win, linux
    return self.path(f"/usr/bin/{name}")

  def sh_stdout_bytes(self,
                      *args: Union[str, pathlib.Path],
                      shell: bool = False,
                      quiet: bool = False,
                      stdin=None,
                      env: Optional[Mapping[str, str]] = None,
                      check: bool = True) -> bytes:
    del shell, quiet, stdin, env, check
    if self._expected_sh_cmds is not None:
      assert self._expected_sh_cmds, (
          f"Missing expected sh_cmds, but got: {args}")
      # Convert all args to str first, sh accepts both str and Paths.
      expected = tuple(map(str, self._expected_sh_cmds[0]))
      str_args = tuple(map(str, args))
      assert expected == str_args, (f"After {len(self._sh_cmds)} cmds: \n"
                                    f"  expected: {expected}\n"
                                    f"  got:      {str_args}")
      self._expected_sh_cmds.pop(0)
    self._sh_cmds.append(args)
    if not self._sh_results:
      cmd = shlex.join(map(str, args))
      raise ValueError(f"After {len(self._sh_cmds)} cmds: "
                       f"MockPlatform has no more sh outputs for cmd: {cmd}")
    return self._sh_results.pop(0)

  def sh(self,
         *args: Union[str, pathlib.Path],
         shell: bool = False,
         capture_output: bool = False,
         stdout=None,
         stderr=None,
         stdin=None,
         env: Optional[Mapping[str, str]] = None,
         quiet: bool = False,
         check: bool = False):
    del capture_output, stderr, stdin, stdout
    self.sh_stdout(*args, shell=shell, quiet=quiet, env=env, check=check)
    # TODO: Generalize this in the future, to mimic failing `sh` calls.
    return subprocess.CompletedProcess(args, 0)

  def popen(self,
            *args: Union[str, pathlib.Path],
            bufsize=-1,
            shell: bool = False,
            stdout=None,
            stderr=None,
            stdin=None,
            env: Optional[Mapping[str, str]] = None,
            quiet: bool = False) -> MockPopen:
    del bufsize, stdout, stderr, stdin
    self.sh_stdout(*args, shell=shell, quiet=quiet, env=env)

    if not self.popens:
      raise ValueError("No valid mock popen.")

    return self.popens.pop(0)

  def mkdir(self,
            path: pth.AnyPathLike,
            parents: bool = True,
            exist_ok: bool = True) -> None:
    super().mkdir(path, parents, exist_ok)
    self.mkdir_calls += 1


class MockFd:

  def __init__(self):
    self.expected_writes: List[bytes] = []
    self.read_returns: List[bytes] = []

  def __del__(self):
    assert not self.expected_writes
    assert not self.read_returns

  def write(self, data: bytes):
    if not self.expected_writes:
      raise ValueError("No expected writes.")

    expected = self.expected_writes.pop(0)

    assert data == expected, (
        f"Expected write does not match. Expected: {expected} Got: {data}")

  def readline(self):
    if not self.read_returns:
      raise ValueError("No read returns.")

    return self.read_returns.pop(0)

  def flush(self):
    return


class MockPopen:

  def __init__(self, stdout: MockFd, stdin: MockFd):
    self._stdout: MockFd = stdout
    self._stdin: MockFd = stdin

  def poll(self):
    return

  def kill(self):
    return

  def wait(self):
    return

  @property
  def stdin(self):
    return self._stdin

  @property
  def stdout(self):
    return self._stdout

class PosixMockPlatformMixin(MockPlatformMixin):
  pass


class WinMockPlatformMixin(MockPlatformMixin):
  # TODO: use wrapper fake path to get windows-path formatting by default
  # when running on posix.

  def path(self, path: pth.AnyPathLike) -> pth.AnyPath:
    return pathlib.PureWindowsPath(path)


class LinuxMockPlatform(PosixMockPlatformMixin, LinuxPlatform):
  pass


class LinuxSshMockPlatform(PosixMockPlatformMixin, LinuxSshPlatform):
  pass


class ChromeOsSshMockPlatform(PosixMockPlatformMixin, ChromeOsSshPlatform):
  pass


class MacOsMockPlatform(PosixMockPlatformMixin, MacOSPlatform):
  pass


class WinMockPlatform(WinMockPlatformMixin, WinPlatform):
  pass


class MockAdb(Adb):

  def start_server(self) -> None:
    pass

  def stop_server(self) -> None:
    pass

  def kill_server(self) -> None:
    pass


class AndroidAdbMockPlatform(MockPlatformMixin, AndroidAdbPlatform):
  pass


class GenericMockPlatform(MockPlatformMixin, Platform):
  pass


if plt.PLATFORM.is_linux:
  MockPlatform = LinuxMockPlatform
elif plt.PLATFORM.is_macos:
  MockPlatform = MacOsMockPlatform
elif plt.PLATFORM.is_win:
  MockPlatform = WinMockPlatform
else:
  raise RuntimeError(f"Unsupported platform: {plt.PLATFORM}")


class MockStory(Story):

  @classmethod
  def all_story_names(cls):
    return ["story_1", "story_2"]

  def run(self, run: Run) -> None:
    pass


class MockBenchmark(SubStoryBenchmark):
  NAME = "mock-benchmark"
  DEFAULT_STORY_CLS = MockStory


class MockCLI(CrossBenchCLI):
  runner: Runner
  platform: Platform

  def __init__(self, *args, **kwargs) -> None:
    self.platform = kwargs.pop("platform")
    super().__init__(*args, **kwargs)

  def _get_runner(self, args, benchmark, env_config, env_validation_mode,
                  timing):
    if not args.out_dir:
      # Use stable mock out dir
      args.out_dir = pathlib.Path("/results")
      assert not args.out_dir.exists()
    runner_kwargs = self.RUNNER_CLS.kwargs_from_cli(args)
    self.runner = self.RUNNER_CLS(
        benchmark=benchmark,
        env_config=env_config,
        env_validation_mode=env_validation_mode,
        timing=timing,
        **runner_kwargs,
        # Use custom platform
        platform=self.platform)
    return self.runner
