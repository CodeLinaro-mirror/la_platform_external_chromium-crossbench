# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import io
import json
import logging
import shlex
import subprocess
import time
from typing import IO, TYPE_CHECKING, Final, Mapping, cast, override

from crossbench.plt import android_adb
from crossbench.plt.pyodide import JsBuffer, PyodideGcsBlob, PyodidePlatform, \
    is_pyodide_env

if TYPE_CHECKING:
  from collections.abc import Buffer

  from crossbench import path as pth
  from crossbench.flags.base import FlagsData
  from crossbench.plt.base import Platform
  from crossbench.plt.pyodide import WebAdb
  from crossbench.plt.signals import Signals
  from crossbench.plt.types import CmdArg, ProcessIo
  from crossbench.types import JsonDict

try:
  import js
except ImportError:
  js = None


class PyodideAdb(android_adb.Adb):
  """ADB implementation that delegates to JavaScript js.webadb via Pyodide."""

  def __init__(
      self,
      host_platform: Platform | None = None,
      device_identifier: str | None = None,
      webadb: WebAdb | None = None,
  ) -> None:
    if webadb is None and js is not None:
      webadb = js.webadb
    if webadb is None:
      raise ValueError("PyodideAdb requires a valid webadb JavaScript object.")
    self._webadb: Final[WebAdb] = webadb
    if host_platform is None:
      host_platform = PyodidePlatform(webadb=webadb)
    # Skip native binary discovery by manually initializing Final superclass
    # attributes instead of calling Adb.__init__.
    self._host_platform = host_platform  # pyrefly: ignore[bad-override]
    self._adb_bin = (  # pyrefly: ignore[bad-override]
        host_platform.path("webadb"))
    self._bundletool = None  # pyrefly: ignore[bad-override]
    serial_id, device_info = self._start(device_identifier)
    self._serial_id = serial_id  # pyrefly: ignore[bad-override]
    self._device_info = device_info  # pyrefly: ignore[bad-override]

  @property
  def webadb(self) -> WebAdb:
    return self._webadb

  @override
  def _start(
      self,
      device_identifier: str | None = None,
  ) -> tuple[str, android_adb.AndroidDeviceInfo]:
    serial_id = device_identifier or str(self._webadb.serial)
    device_info = android_adb.AndroidDeviceInfo(
        device_id=serial_id, name="device")
    return serial_id, device_info

  @override
  def devices(self) -> dict[str, android_adb.AndroidDeviceInfo]:
    return {self._serial_id: self._device_info}

  @override
  def start_server(self) -> None:
    pass

  @override
  def kill_server(self) -> None:
    pass

  @override
  def root(self) -> None:
    if self.has_root():
      return
    self._webadb.root()

  @override
  def unroot(self) -> None:
    if not self.has_root():
      return
    self._webadb.unroot()

  @override
  def push(
      self,
      local_src_path: pth.LocalPath,
      device_dest_path: pth.AnyPath,
  ) -> None:
    self._check_interrupted()
    local_src = self._host_platform.local_path(local_src_path)
    remote_dest = str(device_dest_path)
    try:
      self._webadb.push(str(local_src), remote_dest)
    except Exception as e:
      if "BenchmarkExecutionInterrupted" in str(e) or "Stopped by user" in str(
          e):
        self._webadb.acknowledgeInterrupt()
        raise KeyboardInterrupt(
            "Benchmark execution interrupted by user") from None
      raise

  @override
  def pull(
      self,
      device_src_path: pth.AnyPath,
      local_dest_path: pth.LocalPath,
  ) -> None:
    self._check_interrupted()
    remote_src = str(device_src_path)
    local_dest = self._host_platform.local_path(local_dest_path)
    try:
      self._webadb.pull(remote_src, str(local_dest))
    except Exception as e:
      if "BenchmarkExecutionInterrupted" in str(e) or "Stopped by user" in str(
          e):
        self._webadb.acknowledgeInterrupt()
        raise KeyboardInterrupt(
            "Benchmark execution interrupted by user") from None
      raise

  @override
  def forward(
      self,
      local: int,
      remote: int | str,
      local_protocol: str = "tcp",
      remote_protocol: str = "tcp",
      flags_data: FlagsData = None,
  ) -> int:
    del local, remote, local_protocol, remote_protocol, flags_data
    raise NotImplementedError("Port forwarding is not supported on Pyodide.")

  @override
  def forward_remove(self, local: int, protocol: str = "tcp") -> None:
    del local, protocol
    raise NotImplementedError("Port forwarding is not supported on Pyodide.")

  @override
  def reverse(self, remote: int, local: int, protocol: str = "tcp") -> int:
    del remote, local, protocol
    raise NotImplementedError(
        "Reverse port forwarding is not supported on Pyodide.")

  @override
  def reverse_remove(self, remote: int, protocol: str = "tcp") -> None:
    del remote, protocol
    raise NotImplementedError(
        "Reverse port forwarding is not supported on Pyodide.")

  def _check_interrupted(self) -> None:
    if self._webadb and self._webadb.isInterrupted():
      self._webadb.acknowledgeInterrupt()
      raise KeyboardInterrupt("Benchmark execution interrupted by user")

  def _run_shell(
      self,
      cmd_str: str,
      input: bytes | None = None,  # pylint: disable=redefined-builtin
  ) -> bytes:
    self._check_interrupted()
    try:
      if input is None:
        raw = self._webadb.shell(cmd_str)
      else:
        raw = self._webadb.shell(cmd_str, input.decode("utf-8"))
      return self._to_bytes(raw)
    except Exception as e:
      if "BenchmarkExecutionInterrupted" in str(e) or "Stopped by user" in str(
          e):
        self._webadb.acknowledgeInterrupt()
        raise KeyboardInterrupt(
            "Benchmark execution interrupted by user") from None
      raise

  # Required to overcome the "emscripten does not support processes" error.
  @override
  def _adb(
      self,
      *args: CmdArg,
      shell: bool = False,
      capture_output: bool = False,
      stdout: ProcessIo = None,
      stderr: ProcessIo = None,
      stdin: ProcessIo = None,
      input: bytes | None = None,  # pylint: disable=redefined-builtin
      quiet: bool = False,
      check: bool = True,
      use_serial_id: bool = True,
  ) -> subprocess.CompletedProcess:
    del shell, capture_output, stdout, stderr, stdin, quiet, check
    del use_serial_id
    self._check_interrupted()
    if not args:
      raise ValueError("No arguments provided to _adb")
    cmd = str(args[0])
    sub_args = args[1:]
    if cmd != "shell":
      raise NotImplementedError(
          f"ADB command '{cmd}' is not supported on Pyodide.")
    return self.shell(*sub_args, input=input)

  @override
  def _adb_stdout_bytes(
      self,
      *args: CmdArg,
      quiet: bool = False,
      stdin: ProcessIo = None,
      input: bytes | None = None,  # pylint: disable=redefined-builtin
      use_serial_id: bool = True,
      check: bool = True,
  ) -> bytes:
    del quiet, stdin, use_serial_id, check
    res = self._adb(*args, input=input)
    assert isinstance(res.stdout, bytes)
    return res.stdout

  def _build_shell_cmd_str(
      self,
      *args: CmdArg,
      shell: bool = False,
  ) -> str:
    if not shell:
      return shlex.join(map(str, args))
    if len(args) == 1:
      return str(args[0])
    raise ValueError(f"Expected single sh arg with shell=True, but got: {args}")

  def _to_bytes(self, raw: str | bytes | JsBuffer) -> bytes:
    if isinstance(raw, bytes):
      return raw
    if isinstance(raw, str):
      return raw.encode("utf-8")
    return raw.to_bytes()

  @override
  def shell(
      self,
      *args: CmdArg,
      shell: bool = False,
      capture_output: bool = False,
      stdout: ProcessIo = None,
      stderr: ProcessIo = None,
      stdin: ProcessIo = None,
      input: bytes | None = None,  # pylint: disable=redefined-builtin
      env: Mapping[str, str] | None = None,
      cwd: pth.AnyPath | None = None,
      quiet: bool = False,
      check: bool = True,
  ) -> subprocess.CompletedProcess:
    del capture_output, stdout, stderr, stdin, env, cwd, quiet
    del check
    cmd_str = self._build_shell_cmd_str(*args, shell=shell)
    out = self._run_shell(cmd_str, input=input)
    return subprocess.CompletedProcess(
        args=args, returncode=0, stdout=out, stderr=b"")

  @override
  def shell_stdout_bytes(
      self,
      *args: CmdArg,
      shell: bool = False,
      quiet: bool = False,
      stdin: ProcessIo = None,
      input: bytes | None = None,  # pylint: disable=redefined-builtin
      env: Mapping[str, str] | None = None,
      cwd: pth.AnyPath | None = None,
      check: bool = True,
  ) -> bytes:
    del quiet, stdin, env, cwd, check
    cmd_str = self._build_shell_cmd_str(*args, shell=shell)
    return self._run_shell(cmd_str, input=input)


class PyodideAndroidAdbPlatform(android_adb.AndroidAdbPlatform):
  """Android ADB Platform running in a Pyodide WebAssembly environment."""

  def __init__(
      self,
      host_platform: Platform | None = None,
      device_identifier: str | None = None,
      adb: android_adb.Adb | None = None,
      webadb: WebAdb | None = None,
  ) -> None:
    if host_platform is None:
      host_platform = PyodidePlatform(webadb=webadb)
    adb = adb or PyodideAdb(
        host_platform=host_platform,
        device_identifier=device_identifier,
        webadb=webadb,
    )
    super().__init__(
        host_platform=host_platform,
        device_identifier=device_identifier,
        adb=adb,
    )

  @property
  def is_pyodide(self) -> bool:
    return True

  @property
  def webadb(self) -> WebAdb:
    assert isinstance(self.adb, PyodideAdb)
    return self.adb.webadb

  @override
  def get_gcs_blob(self, gcs_url: str) -> PyodideGcsBlob:
    blob = self.host_platform.get_gcs_blob(gcs_url)
    assert isinstance(blob, PyodideGcsBlob)
    return blob

  def _check_interrupted(self) -> None:
    if self.webadb and self.webadb.isInterrupted():
      self.webadb.acknowledgeInterrupt()
      raise KeyboardInterrupt("Benchmark execution interrupted by user")

  @override
  def sleep(self, seconds: float | dt.timedelta) -> None:
    total_secs = (
        seconds.total_seconds()
        if isinstance(seconds, dt.timedelta) else float(seconds))
    if total_secs <= 0:
      return
    start = time.time()
    while time.time() - start < total_secs:
      self._check_interrupted()
      step = min(0.05, total_secs - (time.time() - start))
      if step <= 0:
        break
      time.sleep(step)

  @override
  def start_devtools(self) -> None:
    self._check_interrupted()
    res = self.webadb.startDevTools()
    if not res:
      raise RuntimeError("Failed to start DevTools connection in Pyodide")

  @override
  def stop_devtools(self) -> None:
    self.webadb.stopDevTools()

  @override
  def switch_to_new_tab(self, url: str = "about:blank") -> None:
    self._check_interrupted()
    self.webadb.switchTab(url)

  @override
  def send_cdp_command(self,
                       method: str,
                       params: JsonDict | None = None) -> JsonDict:
    self._check_interrupted()
    try:
      res_str = self.webadb.sendCdpCommand(method, json.dumps(params or {}))
    except Exception as e:
      if "BenchmarkExecutionInterrupted" in str(e) or "Stopped by user" in str(
          e):
        self.webadb.acknowledgeInterrupt()
        raise KeyboardInterrupt(
            "Benchmark execution interrupted by user") from None
      raise
    if not res_str:
      raise RuntimeError(
          f"Pyodide sendCdpCommand('{method}') returned empty response")
    res = json.loads(str(res_str))
    if "error" in res:
      raise RuntimeError(f"CDP command '{method}' failed: {res['error']}")
    return {"id": 1, "result": res}

  def _check_path(self, flag: str, path: pth.AnyPathLike) -> bool:
    quoted_path = shlex.quote(str(self.path(path)))
    out = self.sh_stdout(  # noqa: S604
        f"[ {flag} {quoted_path} ] && echo 1", shell=True)
    return out.strip() == "1"

  @override
  def exists(self, path: pth.AnyPathLike) -> bool:
    return self._check_path("-e", path)

  @override
  def is_file(self, path: pth.AnyPathLike) -> bool:
    return self._check_path("-f", path)

  @override
  def is_dir(self, path: pth.AnyPathLike) -> bool:
    return self._check_path("-d", path)

  @override
  def write_text(
      self,
      file: pth.AnyPathLike,
      data: str,
      encoding: str = "utf-8",
  ) -> None:
    del encoding
    self._check_interrupted()
    dest_file = shlex.quote(str(self.path(file)))
    content = shlex.quote(data)
    self.adb.shell(  # noqa: S604
        f"echo -n {content} > {dest_file}", shell=True)

  @override
  def _popen(
      self,
      *args: CmdArg,
      bufsize: int = -1,
      shell: bool = False,
      stdout: ProcessIo = None,
      stderr: ProcessIo = None,
      stdin: ProcessIo = None,
      env: Mapping[str, str] | None = None,
      cwd: pth.AnyPath | None = None,
      encoding: str | None = None,
      quiet: bool = False,
      auto_terminate: bool = True,
  ) -> subprocess.Popen:
    del shell, bufsize, quiet, encoding, auto_terminate
    assert not env, "ADB does not support env vars"
    self._check_interrupted()

    cmd_str = shlex.join(map(str, args))
    if cwd:
      cmd_str = f"cd {shlex.quote(str(cwd))} && {cmd_str}"

    logging.info("Starting background process via WebADB spawn: %s", cmd_str)
    proc_id = int(self.webadb.spawnProcess(cmd_str))
    local_file: IO[str] | None = None
    if isinstance(stdout, io.IOBase):
      local_file = cast(IO[str], stdout)
    popen_obj = PyodideStreamingPopen(
        self,
        proc_id=proc_id,
        cmd=cmd_str,
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        local_log_file=local_file,
    )
    popen_obj.poll()
    return popen_obj


class PyodidePopenStdin(io.RawIOBase):
  """Writable stdin stream for a PyodideStreamingPopen process."""

  def __init__(
      self,
      platform: PyodideAndroidAdbPlatform,
      proc_id: int,
  ) -> None:
    super().__init__()
    self._platform: Final[PyodideAndroidAdbPlatform] = platform
    self._proc_id: Final[int] = proc_id

  @override
  def writable(self) -> bool:
    return True

  @override
  def write(self, b: Buffer, /) -> int:
    if self.closed:
      raise ValueError("write to closed file")
    raw_bytes = bytes(b)
    if not raw_bytes:
      return 0
    text = raw_bytes.decode("utf-8")
    try:
      self._platform.webadb.writeProcessStdin(self._proc_id, text)
    except Exception as e:
      raise BrokenPipeError(str(e)) from e
    return len(raw_bytes)

  @override
  def close(self) -> None:
    if self.closed:
      return
    super().close()
    self._platform.webadb.closeProcessStdin(self._proc_id)


class PyodideStreamingPopen(subprocess.Popen):
  """A wrapper class to represent a streaming process spawned over WebADB.

  Keeps the ADB stream open and continuously synchronizes stdout/stderr to
  the local file without terminating the remote session.
  """

  def __init__(
      self,
      platform: PyodideAndroidAdbPlatform,
      proc_id: int,
      cmd: str,
      stdout: ProcessIo = None,
      stderr: ProcessIo = None,
      stdin: ProcessIo = None,
      local_log_file: IO[str] | None = None,
  ) -> None:
    self._platform: Final[PyodideAndroidAdbPlatform] = platform
    self._proc_id: Final[int] = proc_id
    self._cmd: Final[str] = cmd
    self._local_log_file: Final[IO[str] | None] = local_log_file
    self._last_log_offset: int = 0
    self.returncode: int | None = None
    self.args = cmd
    self.pid = proc_id
    self.stdout = None
    self.stderr = None
    self.stdin = None
    if stdin == subprocess.PIPE:
      self.stdin = cast(IO[bytes],
                        PyodidePopenStdin(self._platform, self._proc_id))
    if stdout == subprocess.PIPE or stderr == subprocess.PIPE:
      raise ValueError(
          "stdout/stderr PIPE is not supported in PyodideStreamingPopen")

  @property
  def proc_id(self) -> int:
    return self._proc_id

  @override
  def poll(self) -> int | None:
    if self.returncode is not None:
      return self.returncode
    self._sync_logs()
    return self.returncode

  def _sync_logs(self) -> None:
    webadb = self._platform.webadb
    raw_status = webadb.readProcessLog(self._proc_id, self._last_log_offset)
    if not raw_status:
      return
    try:
      status = json.loads(str(raw_status))
    except (ValueError, TypeError) as e:
      logging.warning("Failed to parse readProcessLog JSON: %s", e)
      return

    new_text = status.get("text", "")
    next_offset = status.get("nextOffset", self._last_log_offset)
    is_exited = status.get("isExited", False)
    exit_code = status.get("exitCode")

    if new_text and self._local_log_file:
      self._local_log_file.write(new_text)
      self._local_log_file.flush()

    self._last_log_offset = next_offset
    if is_exited and self.returncode is None:
      self.returncode = exit_code if exit_code is not None else 0

  @override
  def wait(self, timeout: float | None = None) -> int:
    start_time = time.time()
    while self.poll() is None:
      if timeout and (time.time() - start_time) > timeout:
        raise subprocess.TimeoutExpired(self._cmd, timeout)
      time.sleep(0.1)
    assert self.returncode is not None
    return self.returncode

  @override
  def send_signal(self, sig: int | Signals) -> None:
    if self.returncode is not None:
      return
    self._platform.webadb.killProcess(self._proc_id)
    self.returncode = -int(sig)
    self._sync_logs()

  @override
  def terminate(self) -> None:
    self.send_signal(self._platform.signals.SIGTERM)

  @override
  def kill(self) -> None:
    self.send_signal(self._platform.signals.SIGKILL)


__all__ = [
    "PyodideAdb",
    "PyodideAndroidAdbPlatform",
    "PyodideGcsBlob",
    "PyodidePlatform",
    "PyodidePopenStdin",
    "PyodideStreamingPopen",
    "is_pyodide_env",
]
