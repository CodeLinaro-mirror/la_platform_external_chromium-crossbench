# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import contextlib
import datetime as dt
import json
import logging
from typing import IO, TYPE_CHECKING, Any, ClassVar, Iterator, Self

from typing_extensions import override

from crossbench.parse import DurationParser, PathParser
from crossbench.probes.probe import Probe, ProbeConfigParser, ProbeContext, \
    ProbeIncompatibleBrowser

if TYPE_CHECKING:
  import subprocess

  from crossbench import path as pth
  from crossbench.browsers.browser import Browser
  from crossbench.env.runner_env import RunnerEnv
  from crossbench.probes.results import ProbeResult
  from crossbench.runner.run import Run


class BitsProbe(Probe):
  """
  Probe for the external BITS/Kibble power measurement tool.
  Starts BITS in the background on the host during the run
  and stops it afterwards.
  """
  NAME: ClassVar[str] = "bits"
  DEFAULT_DURATION: ClassVar[dt.timedelta] = dt.timedelta(seconds=99999)

  @classmethod
  @override
  def config_parser(cls) -> ProbeConfigParser[Self]:
    parser = super().config_parser()
    parser.add_argument(
        "bits_path",
        aliases=("path",),
        type=PathParser.existing_file_path,
        required=True,
        help="Path to the BITS external tool binary on the host.")
    parser.add_argument(
        "bits_out",
        aliases=(
            "out",
            "collection",
        ),
        type=str,
        required=False,
        default="",
        help="Output identifier for the BITS tool.")
    parser.add_argument(
        "bits_device",
        aliases=("device",),
        type=str,
        default="",
        help="Device identifier for the BITS tool.")
    parser.add_argument(
        "duration",
        type=DurationParser.positive_duration,
        default=cls.DEFAULT_DURATION,
        help="Duration for the BITS tool to run.")
    return parser

  def __init__(
      self,
      bits_path: pth.LocalPath,
      bits_out: str = "",
      bits_device: str = "",
      duration: dt.timedelta = DEFAULT_DURATION,
  ) -> None:
    super().__init__()
    if duration < dt.timedelta(seconds=1):
      raise ValueError(f"Duration must be at least 1s, but got: {duration}")
    self._bits_path: pth.LocalPath = bits_path
    self._bits_out: str = bits_out
    self._bits_device: str = bits_device
    self._duration: dt.timedelta = duration

  @property
  def bits_path(self) -> pth.LocalPath:
    return self._bits_path

  @property
  def bits_out(self) -> str:
    return self._bits_out

  @property
  def bits_device(self) -> str:
    return self._bits_device

  @property
  def duration(self) -> dt.timedelta:
    return self._duration


  @override
  def validate_browser(self, env: RunnerEnv, browser: Browser) -> None:
    super().validate_browser(env, browser)
    if not browser.platform.is_android:
      raise ProbeIncompatibleBrowser(
          self, browser, "BITS probe is only supported on Android devices.")

  @override
  def get_context_cls(self) -> type[BitsProbeContext]:
    return BitsProbeContext


class BitsProbeContext(ProbeContext[BitsProbe]):

  def __init__(self, probe: BitsProbe, run: Run) -> None:
    super().__init__(probe, run)
    self._process: subprocess.Popen | None = None
    self._bits_out_id = self.probe.bits_out or dt.datetime.now().strftime(
        "%Y%m%d_%H%M%S")

  @property
  def bits_out_id(self) -> str:
    return self._bits_out_id

  @contextlib.contextmanager
  def _log_files(self, mode: str) -> Iterator[tuple[IO[Any], IO[Any]]]:
    stdout_path = self.local_result_path / "stdout.txt"
    stderr_path = self.local_result_path / "stderr.txt"
    with stdout_path.open(mode, encoding="utf-8") as stdout, \
         stderr_path.open(mode, encoding="utf-8") as stderr:
      yield stdout, stderr

  def _start_collection(self) -> None:
    logging.debug("BITS: Starting collection (ID: %r)", self.bits_out_id)
    self.host_platform.mkdir(self.local_result_path)

    json_path = self.local_result_path / "bits.json"
    self.host_platform.write_text(
        json_path,
        json.dumps({"bits_out_id": self.bits_out_id}, indent=2),
    )

    device_args: tuple[str, ...] = ()
    if self.probe.bits_device:
      device_args += ("--device", self.probe.bits_device)

    with self._log_files("w") as (stdout, stderr):
      self._process = self.host_platform.popen(
          self.probe.bits_path,
          "--create",
          self.bits_out_id,
          "--duration",
          f"{self.probe.duration.total_seconds():.0f}s",
          *device_args,
          stdout=stdout,
          stderr=stderr,
      )

  def _stop_collection(self) -> None:
    logging.debug("BITS: Stopping collection (ID: %r)", self.bits_out_id)
    stop_args = (
        self.probe.bits_path,
        "--stop",
        self.bits_out_id,
    )
    with self._log_files("a") as (stdout, stderr):
      self.host_platform.sh(*stop_args, stdout=stdout, stderr=stderr)

  @override
  def start(self) -> None:
    pass

  @override
  def start_story_run(self) -> None:
    self._start_collection()

  @override
  def stop_story_run(self) -> None:
    self._stop_collection()

  @override
  def stop(self) -> None:
    pass

  @override
  def teardown(self) -> ProbeResult:
    if self.host_platform.exists(self.local_result_path):
      files = [
          f for f in self.local_result_path.iterdir()
          if self.host_platform.is_file(f)
      ]
      return self.local_result(file=files)
    return self.empty_result()
