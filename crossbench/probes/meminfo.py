# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import csv
import dataclasses
from typing import TYPE_CHECKING, Optional, Self, Type

from typing_extensions import override

from crossbench import path as pth
from crossbench.action_runner.action.meminfo import MeminfoTarget
from crossbench.probes.probe import Probe, ProbeConfigParser
from crossbench.probes.probe_context import ProbeContext
from crossbench.probes.result_location import ResultLocation

if TYPE_CHECKING:
  from crossbench.path import AnyPath
  from crossbench.probes.results import ProbeResult
  from crossbench.runner.run import Run


class MeminfoProbe(Probe):
  """
    General-purpose Probe that records the specified meminfo.
    """

  NAME = "meminfo"
  RESULT_LOCATION = ResultLocation.LOCAL

  @classmethod
  @override
  def config_parser(cls) -> ProbeConfigParser[Self]:
    parser = super().config_parser()
    return parser

  @override
  def get_context_cls(self) -> Type[MeminfoProbeContext]:
    return MeminfoProbeContext


class MeminfoProbeContext(ProbeContext[MeminfoProbe]):

  def __init__(self, probe: MeminfoProbe, run: Run) -> None:
    super().__init__(probe, run)
    self._results: list[AnyPath] = []

  @override
  def get_default_result_path(self) -> AnyPath:
    dump_dir = super().get_default_result_path()
    self.host_platform.mkdir(dump_dir)
    return dump_dir

  def start(self) -> None:
    pass

  def stop(self) -> None:
    pass

  def dump_meminfo(self, target: MeminfoTarget, package: Optional[str]) -> None:
    timestamp = self.browser_platform.sh_stdout("date",
                                                "+%Y-%m-%d %H:%M:%S").rstrip()

    if target is MeminfoTarget.BROWSER:
      meminfo = self.browser.meminfo()
      package_path = self.browser.unique_name
    elif package is not None:
      meminfo = self.browser_platform.meminfo(package)
      package_path = pth.safe_filename(package).lower()
    else:
      raise ValueError("Cannot dump meminfo without package name.")

    meminfo_json = []
    for proc_name, proc_meminfo in meminfo.items():
      proc_data = dataclasses.asdict(proc_meminfo)
      proc_data["timestamp"] = timestamp
      proc_data["name"] = proc_name
      meminfo_json.append(proc_data)

    self.browser.performance_mark("meminfo", detail=meminfo_json)

    csv_path = self.result_path / package_path / "meminfo.csv"

    self.host_platform.mkdir(csv_path.parent, parents=True, exist_ok=True)

    write_header = False

    if not self.host_platform.exists(csv_path):
      write_header = True
      self._results.append(csv_path)

    with open(csv_path, "a", encoding="utf-8", newline="") as f:
      writer = csv.DictWriter(
          f,
          [
              "timestamp",
              "pid",
              "name",
              "pss_total",
              "rss_total",
              "swap_total",
          ],
      )
      if write_header:
        writer.writeheader()
      writer.writerows(meminfo_json)

  @override
  def teardown(self) -> ProbeResult:
    if not self.browser_platform.is_dir(self.result_path):
      return self.empty_result()
    return self.browser_result(file=tuple(self._results))
