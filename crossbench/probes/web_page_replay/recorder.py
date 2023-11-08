# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import atexit
import logging
import pathlib
import re
import shutil
import signal
import subprocess
import time
from typing import TYPE_CHECKING, Iterable, List, Optional, TextIO, Tuple

from crossbench import cli_helper, helper, plt
from crossbench.browsers.chromium.chromium import Chromium
from crossbench.probes import helper as probe_helper
from crossbench.probes.probe import Probe, ProbeConfigParser, ProbeContext
from crossbench.probes.results import EmptyProbeResult, ProbeResult

if TYPE_CHECKING:
  from crossbench.browsers.browser import Browser
  from crossbench.runner.run import Run

from crossbench.runner.groups import BrowsersRunGroup, RepetitionsRunGroup, RunGroup, StoriesRunGroup


class WebPageReplayProbe(Probe):
  """
  Probe to collect browser requests to wpr.go archive which then can be
  replayed using a local proxy server.

  Chrome telemetry's wpr.go:
  https://chromium.googlesource.com/catapult/+/HEAD/web_page_replay_go/README.md
  """

  NAME = "wpr"

  @classmethod
  def config_parser(cls) -> ProbeConfigParser:
    parser = super().config_parser()
    parser.add_argument("http_port", type=int, default=8080, required=False)
    parser.add_argument("https_port", type=int, default=8081, required=False)
    parser.add_argument(
        "wpr_go_bin", type=cli_helper.parse_binary_path, required=False)
    parser.add_argument(
        "key_file", type=cli_helper.parse_existing_file_path, required=False)
    parser.add_argument(
        "cert_file", type=cli_helper.parse_existing_file_path, required=False)
    parser.add_argument(
        "inject_scripts",
        is_list=True,
        type=cli_helper.parse_existing_file_path,
        required=False)
    parser.add_argument(
        "use_test_root_certificate", type=bool, default=False, required=False)
    return parser

  def __init__(self,
               http_port: int = 0,
               https_port: int = 0,
               wpr_go_bin: Optional[pathlib.Path] = None,
               inject_scripts: Optional[Iterable[pathlib.Path]] = None,
               key_file: Optional[pathlib.Path] = None,
               cert_file: Optional[pathlib.Path] = None,
               use_test_root_certificate: bool = False):
    super().__init__()
    if http_port == https_port:
      raise ValueError("http_port must be different from https_port, "
                       f"but got twice: {http_port}")
    self._http_port = http_port
    self._https_port = https_port

    self._use_test_root_certificate = use_test_root_certificate
    if not self.runner_platform.which("go"):
      raise ValueError(f"'go' binary not available on r{self.runner_platform}")

    if not wpr_go_bin:
      wpr_go_bin = WprGoToolFinder(plt.PLATFORM).path
    if not wpr_go_bin:
      raise ValueError("Could not find wpr.go binary")
    if wpr_go_bin.exists():
      raise ValueError(f"wpr.go binary does not exist: {wpr_go_bin}")
    self._wpr_go_bin = wpr_go_bin
    wpr_root = self.wpr_go_bin.parents[1]

    if key_file:
      self._key_file = key_file
    else:
      self._key_file = wpr_root / "ecdsa_key.pem"
    if not self._key_file.is_file():
      raise ValueError(f"Could not find ecdsa_key.pem file: {self._key_file}")

    if cert_file:
      self._cert_file = cert_file
    else:
      self._cert_file = wpr_root / "ecdsa_cert.pem"
    if not self._cert_file.is_file():
      raise ValueError(f"Could not find ecdsa_cert.pem file: {self._cert_file}")

    if inject_scripts is None:
      inject_scripts = [wpr_root / "deterministic.js"]
    for script in inject_scripts:
      if "," in str(script):
        raise ValueError(f"Injected script path cannot contain ',': {script}")
      if not script.is_file():
        raise ValueError(f"Injected script does not exist: {script}")
    self._inject_scripts = tuple(inject_scripts)

  @property
  def https_port(self) -> int:
    return self._https_port

  @property
  def http_port(self) -> int:
    return self._http_port

  @property
  def wpr_go_bin(self) -> pathlib.Path:
    return self._wpr_go_bin

  @property
  def inject_scripts(self) -> Optional[Tuple[pathlib.Path, ...]]:
    return self._inject_scripts

  @property
  def key_file(self) -> pathlib.Path:
    return self._key_file

  @property
  def cert_file(self) -> pathlib.Path:
    return self._cert_file

  @property
  def use_test_root_certificate(self) -> bool:
    return self._use_test_root_certificate

  @property
  def result_path_name(self) -> str:
    return "archive.wprgo"

  def is_compatible(self, browser: Browser) -> bool:
    return isinstance(browser, Chromium) and browser.platform.is_local

  def get_context(self, run: Run) -> WebPageReplayRecorderProbeContext:
    return WebPageReplayRecorderProbeContext(self, run)

  def merge_repetitions(self, group: RepetitionsRunGroup) -> ProbeResult:
    results = [run.results[self].file for run in group.runs]
    return self.merge_group(results, group)

  def merge_stories(self, group: StoriesRunGroup) -> ProbeResult:
    results = [
        subgroup.results[self].file for subgroup in group.repetitions_groups
    ]
    return self.merge_group(results, group)

  def merge_browsers(self, group: BrowsersRunGroup) -> ProbeResult:
    results = [subgroup.results[self].file for subgroup in group.story_groups]
    return self.merge_group(results, group)

  def merge_group(self, results: List[pathlib.Path],
                  group: RunGroup) -> ProbeResult:
    result_file = group.get_local_probe_result_path(self)
    if not results:
      return EmptyProbeResult()
    first_wprgo = results.pop(0)
    # TODO migrate to platform
    shutil.copy(first_wprgo, result_file)
    for repetition_file in results:
      self.httparchive_merge(repetition_file, result_file)
    return ProbeResult(file=[result_file])

  def httparchive_merge(self, input_archive: pathlib.Path,
                        output_archive: pathlib.Path) -> None:
    cmd = [
        "go",
        "run",
        self.wpr_go_bin.parent / "httparchive.go",
        "merge",
        output_archive,
        input_archive,
        output_archive,
    ]
    with helper.ChangeCWD(self.wpr_go_bin.parent):
      self.runner_platform.sh(*cmd)


_WPR_PORT_RE = re.compile(r".*Starting server on "
                          r"(?P<protocol>http|https)://"
                          r"(?P<host>[^:]+):"
                          r"(?P<port>\d+)")


class WebPageReplayRecorderProbeContext(ProbeContext[WebPageReplayProbe]):

  def __init__(self, probe: WebPageReplayProbe, run: Run) -> None:
    super().__init__(probe, run)
    self._wprgo_recorder_process: Optional[subprocess.Popen] = None
    self._wprgo_log = self.result_path.with_name("wpr_record.log")
    self._wprgo_log_file: Optional[TextIO] = None
    self._host = "127.0.0.1"
    self._http_port = self.probe.http_port
    self._https_port = self.probe.https_port

  def setup(self) -> None:
    self._setup_wpr_go_recorder()
    self._setup_extra_flags()

  def _setup_extra_flags(self) -> None:
    if not self.probe.use_test_root_certificate:
      cert_hash_file = self.probe.cert_file.parent / "wpr_public_hash.txt"
      if not cert_hash_file.is_file():
        raise ValueError(
            f"Could not read public key hash file: {cert_hash_file}")
      cert_skip_list = ",".join(cert_hash_file.read_text().strip().splitlines())
      self.run.extra_flags[
          "--ignore-certificate-errors-spki-list"] = cert_skip_list
    # TODO: support ts_proxy traffic shaping
    # run.extra_flags[
    #     "--proxy-server"] = "socks://{self._ts_proxy_host}:{self._ts_proxy_port}"
    # run.extra_flags["--proxy-bypass-list"] = "<-loopback>"
    self.run.extra_flags["--host-resolver-rules"] = (
        f"MAP *:80 {self._host}:{self._http_port},"
        f"MAP *:443 {self._host}:{self._https_port},"
        "EXCLUDE localhost")
    # TODO: add replay support, see:
    # third_party/catapult/telemetry/telemetry/internal/backends/chrome/chrome_startup_args.py

  def _setup_wpr_go_recorder(self) -> None:
    # TODO: move to separate WPR helper for replaying
    cmd = [
        "go",
        "run",
        self.probe.wpr_go_bin,
        "record",
        f"--http_port={self.probe.http_port}",
        f"--https_port={self.probe.https_port}",
        "--cert_type=ecdsa",
        f"--https_key_file={self.probe.key_file}",
        f"--https_cert_file={self.probe.cert_file}",
    ]
    if self.probe.inject_scripts is not None:
      injected_scripts = ",".join(
          str(path) for path in self.probe.inject_scripts)
      cmd.append(f"--inject_scripts={injected_scripts}")
    cmd.append(self.result_path)

    logging.info("WPR: Starting wpr.go recorder")
    logging.debug("WPR: logging to %s", self._wprgo_log)
    self._wprgo_log_file = self._wprgo_log.open("w")
    with helper.ChangeCWD(self.probe.wpr_go_bin.parent):
      self._wprgo_recorder_process = self.runner_platform.popen(
          *cmd, stdout=self._wprgo_log_file, stderr=self._wprgo_log_file)
    if self._wprgo_recorder_process is None:
      raise ValueError("Could not start wpr.go.\n"
                       f"See log for more details: {self._wprgo_log}")
    logging.info("WPR: waiting for startup")
    self._wait_for_wpr_go_recorder()
    logging.info("WPR: Starting wpr.go recorder: DONE")

  def _wait_for_wpr_go_recorder(self) -> None:
    assert self._wprgo_recorder_process
    atexit.register(self._stop_server)
    with self._wprgo_log.open("r") as log_file:
      while self._wprgo_recorder_process.poll() is None:
        line = log_file.readline()
        if not line:
          time.sleep(0.1)
          continue
        if self._parse_wpr_log_line(line):
          break
    if self._wprgo_recorder_process.poll():
      raise ValueError("Could not start wpr.go.\n"
                       f"See log for more details: {self._wprgo_log}")

    with self._open_wpr_cmd_url("generate-200") as r:
      assert r.status == 200

  def _open_wpr_cmd_url(self, cmd: str):
    test_url = f"http://{self._host}:{self._http_port}/web-page-replay-{cmd}"
    return helper.urlopen(test_url)

  def _parse_wpr_log_line(self, line: str) -> bool:
    if "Failed to start server on" in line:
      logging.error(line)
      raise ValueError(f"Could not start wpr.go server, address in use: {line}")
    line = line.strip()
    if match := _WPR_PORT_RE.match(line):
      protocol = match["protocol"].lower()
      port = int(match["port"])
      if protocol == "http":
        self._http_port = port
      elif protocol == "https":
        self._https_port = port
      else:
        logging.error("WPR: got invalid protocol: %s", line)
      self._host = match["host"]
      if not self._host:
        raise ValueError(f"WPR: could not parse host from: {line}")

    if self._http_port and self._https_port:
      logging.debug("WPR: https_port=%s http_port=%s", self._http_port,
                    self._https_port)
      return True
    return False

  def start(self) -> None:
    pass

  def stop(self) -> None:
    pass

  def tear_down(self) -> ProbeResult:
    self._stop_server()
    return self.browser_result(file=(self.result_path,))

  def _stop_server(self) -> None:
    if self._wprgo_log_file:
      self._wprgo_log_file.close()
      self._wprgo_log_file = None
    if self._wprgo_recorder_process:
      logging.info("WPR: shutting down recorder.")
      try:
        with self._open_wpr_cmd_url("command-exit"):
          pass
      except IOError as e:
        logging.debug("WPR: exit failed: %s", e)
      helper.wait_and_kill(
          self._wprgo_recorder_process, timeout=5, signal=signal.SIGINT)
      self._wprgo_recorder_process = None


class WprGoToolFinder:
  _WPR_GO = pathlib.Path("third_party/catapult/web_page_replay_go/src/wpr.go")

  def __init__(self, platform: plt.Platform) -> None:
    self.platform = platform
    self.path = None
    if maybe_chrome := probe_helper.ChromiumCheckoutFinder(platform).path:
      candidate = (maybe_chrome / self._WPR_GO)
      if self.platform.is_file(candidate):
        self.path = candidate
