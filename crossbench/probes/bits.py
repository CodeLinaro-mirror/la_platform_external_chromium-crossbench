# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import logging
from typing import TYPE_CHECKING, ClassVar, Self

from typing_extensions import override

from crossbench.parse import DurationParser, ObjectParser, PathParser
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
        type=ObjectParser.non_empty_str,
        required=True,
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
      bits_out: str,
      bits_device: str = "",
      duration: dt.timedelta = DEFAULT_DURATION,
  ) -> None:
    super().__init__()
    if not bits_path or not bits_out:
      raise ValueError("Both bits_path and bits_out must be provided "
                       "to enable BITS probe.")
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

  def _start_collection(self) -> None:
    logging.debug("BITS: Starting collection (ID: %r)", self.probe.bits_out)
    device_args: tuple[str, ...] = ()
    if self.probe.bits_device:
      device_args += ("--device", self.probe.bits_device)
    self._process = self.host_platform.popen(
        self.probe.bits_path,
        "--create",
        self.probe.bits_out,
        "--duration",
        f"{self.probe.duration.total_seconds():.0f}s",
        *device_args,
    )

  def _stop_collection(self) -> None:
    logging.debug("BITS: Stopping collection (ID: %r)", self.probe.bits_out)
    stop_args = (
        self.probe.bits_path,
        "--stop",
        self.probe.bits_out,
    )
    self.host_platform.sh(*stop_args)

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
    return self.empty_result()
