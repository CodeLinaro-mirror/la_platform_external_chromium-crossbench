# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Modified from chrome's catapult project.

from __future__ import annotations

import atexit
import fcntl
import locale
import logging
import os
import pathlib
import re
import shlex
import signal
import subprocess
import sys
from typing import List, Optional, Union

from crossbench import cli_helper, helper


class TsProxyServerError(Exception):
  """Catch-all exception for tsProxy Server."""


_PORT_RE = re.compile(r"Started Socks5 proxy server on "
                      r"(?P<host>[^:]*):"
                      r"(?P<port>\d+)")
DEFAULT_TIMEOUT = 5


def parse_ts_socks_proxy_port(output_line):
  if match := _PORT_RE.match(output_line):
    return int(match.group("port"))
  return None


# TODO: improve and double check
TRAFFIC_SETTINGS = {
    "3G-slow": {
        "rtt_ms": 400,
        "in_kbps": 400,
        "out_kbps": 400,
    },
    "3G-regular": {
        "rtt_ms": 300,
        "in_kbps": 1600,
        "out_kbps": 768,
    },
    "3G-fast": {
        "rtt_ms": 150,
        "in_kbps": 1600,
        "out_kbps": 768,
    },
    "4G": {
        "rtt_ms": 170,
        "in_kbps": 9000,
        "out_kbps": 9000,
    },
}


class TsProxyServer:
  """
  TsProxy provides basic latency, download and upload traffic shaping. This
  class provides a programming API to the tsproxy script in
  catapult/third_party/tsproxy/tsproxy.py

  This class can be used as a context manager.
  """

  def __init__(self,
               ts_proxy_path: pathlib.Path,
               host_ip: Optional[str] = None,
               socks_proxy_port: Optional[int] = None,
               http_port: Optional[int] = None,
               https_port: Optional[int] = None,
               rtt_ms: Optional[int] = None,
               in_kbps: Optional[int] = None,
               out_kbps: Optional[int] = None,
               window: Optional[int] = None,
               verbose: bool = False):
    self._is_running = False
    self._ts_proxy_path = cli_helper.parse_existing_file_path(ts_proxy_path)
    self._proc = None
    self._socks_proxy_port = self._initial_socks_proxy_port = socks_proxy_port
    self._host_ip = host_ip
    self._http_port = http_port
    self._https_port = https_port
    self._rtt_ms = rtt_ms
    self._in_kbps = in_kbps
    self._out_kbps = out_kbps
    self._window = window
    self._verbose = verbose

  def _verify_ports(self,
                    http_port: Optional[int] = None,
                    https_port: Optional[int] = None) -> None:
    if bool(http_port) != bool(https_port):
      raise ValueError(
          "Both https and http-port should be specified or omitted, "
          f"but got http_port={http_port} and https_port={https_port}")
    if http_port == https_port:
      raise ValueError("http_port and https_port must be different, "
                       f"got {https_port} twice.")
    if http_port is not None:
      cli_helper.parse_port(http_port, "http_port")
    if https_port is not None:
      cli_helper.parse_port(https_port, "https_port")

  @property
  def socks_proxy_port(self) -> int:
    assert self._socks_proxy_port, "Cannot access port of stopped TsProxy"
    return self._socks_proxy_port

  @property
  def is_running(self) -> bool:
    return self._is_running

  def start(self, timeout: Union[int, float] = DEFAULT_TIMEOUT) -> None:
    """Start TsProxy server and verify that it started."""
    cmd = [
        sys.executable,
        self._ts_proxy_path,
    ]
    if not self._socks_proxy_port:
      # Use port 0 so tsproxy picks a random available port.
      cmd.append("--port=0")
    else:
      cmd.append(f"--port={self._socks_proxy_port}")
    if self._verbose:
      cmd.append("--verbose")
    if self._in_kbps:
      cmd.append(f"--inkbps={self._in_kbps}")
    if self._out_kbps:
      cmd.append(f"--outkbps={self._out_kbps}")
    if self._window:
      cmd.append(f"--window={self._window}")
    if self._rtt_ms:
      cmd.append(f"--rtt={self._rtt_ms}")
    if self._host_ip:
      cmd.append(f"--desthost={self._host_ip}")
    if self._http_port:
      cmd.append(f"--mapports=443:{self._https_port},*:{self._http_port}")
    logging.info("TsProxy: commandline: %s", shlex.join(cmd))
    self._verify_default_encoding()
    # In python3 universal_newlines forces subprocess to encode/decode,
    # allowing per-line buffering.
    self._proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True)
    atexit.register(self.stop)
    logging.debug("TsProxy: fcntl is supported, trying to set "
                  "non blocking I/O for the ts_proxy process")
    fd = self._proc.stdout.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    self._wait_for_startup(timeout)

  def _verify_default_encoding(self) -> None:
    # In python3 subprocess handles encoding/decoding; this warns if it won't
    # be UTF-8.
    encoding = locale.getpreferredencoding()
    if encoding != "UTF-8":
      logging.warning("Decoding will use %s instead of UTF-8", encoding)

  def _wait_for_startup(self, timeout: Union[int, float]) -> None:
    for _ in helper.wait_with_backoff(timeout):
      if self._has_started():
        logging.info("TsProxy: port=%i", self._socks_proxy_port)
        self._is_running = True
        return
    if err := self.stop():
      logging.error("TsProxy: Error stopping WPR server:\n%s", err)
    raise TsProxyServerError(
        f"Starting tsproxy timed out after {timeout} seconds")

  def _has_started(self) -> bool:
    assert not self._is_running
    assert self._proc
    if self._proc.poll() is not None:
      return False
    self._proc.stdout.flush()
    output_line = self._read_line_ts_proxy_stdout(timeout=5)
    logging.debug("TsProxy: output: %s", output_line)
    port = parse_ts_socks_proxy_port(output_line)
    self._socks_proxy_port = cli_helper.parse_port(port, "socks_proxy_port")
    return True

  def _read_line_ts_proxy_stdout(self, timeout: Union[int, float]) -> str:
    for _ in helper.wait_with_backoff(timeout):
      try:
        return self._proc.stdout.readline().strip()
      except IOError as e:
        logging.debug("TsProxy: Error while reading tsproxy line: %s", e)
    return ""

  def _send_command(self,
                    command: str,
                    timeout: Union[int, float] = DEFAULT_TIMEOUT) -> None:
    logging.debug("TsProxy: Sending command to ts_proxy_server: %s", command)
    self._proc.stdin.write(f"{command}\n")
    command_output = self._wait_for_status_response(timeout)
    success = "OK" in command_output
    logging.log(logging.DEBUG if success else logging.ERROR,
                "TsProxy: output:\n%s", "\n".join(command_output))
    if not success:
      raise TsProxyServerError(f"Failed to execute command: {command}")

  def _wait_for_status_response(self, timeout: Union[int, float]) -> List[str]:
    logging.debug("TsProxy: waiting for status response")
    command_output = []
    for _ in helper.wait_with_backoff(timeout):
      self._proc.stdin.flush()
      self._proc.stdout.flush()
      last_output = self._read_line_ts_proxy_stdout(timeout)
      command_output.append(last_output)
      if last_output in ("OK", "ERROR"):
        break
    return command_output

  def set_outbound_ports(self,
                         http_port: int,
                         https_port: int,
                         timeout: Union[int, float] = DEFAULT_TIMEOUT) -> None:
    if self._http_port == http_port and self._https_port == https_port:
      return
    self._verify_ports(http_port, https_port)
    self._send_command(f"set mapports 443:{https_port},*:{http_port}", timeout)
    self._http_port = http_port
    self._https_port = https_port

  def set_traffic_settings(self,
                           rtt_ms: Optional[int] = None,
                           in_kbps: Optional[int] = None,
                           out_kbps: Optional[int] = None,
                           window: Optional[int] = None,
                           timeout=DEFAULT_TIMEOUT) -> None:
    if rtt_ms is not None and self._rtt_ms != rtt_ms:
      assert rtt_ms >= 0, f"Invalid rtt value: {rtt_ms}"
      self._send_command(f"set rtt {rtt_ms}", timeout)
      self._rtt_ms = rtt_ms

    if in_kbps is not None and self._in_kbps != in_kbps:
      assert in_kbps >= 0, f"Invalid in_kbps value: {in_kbps}"
      self._send_command(f"set inkbps {in_kbps}", timeout)
      self._in_kbps = in_kbps

    if out_kbps is not None and self._out_kbps != out_kbps:
      assert out_kbps >= 0, f"Invalid out_kbps value: {out_kbps}"
      self._send_command(f"set outkbps {out_kbps}", timeout)
      self._out_kbps = out_kbps

    if window is not None and self._window != window:
      assert window >= 0, f"Invalid window value: {window}"
      self._send_command(f"set window {window}", timeout)
      self._window = window

  def stop(self) -> Optional[str]:
    if not self._is_running:
      logging.debug("TsProxy: Attempting to stop server that is not running.")
      return None
    if not self._proc:
      return None
    self._send_command("exit")
    helper.wait_and_kill(self._proc, signal=signal.SIGINT)
    _, err = self._proc.communicate()
    self._proc = None
    self._socks_proxy_port = self._initial_socks_proxy_port
    self._is_running = False
    return err

  def __enter__(self):
    self.start()
    return self

  def __exit__(self, unused_exc_type, unused_exc_val, unused_exc_tb):
    self.stop()
