# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, ClassVar, Self, Type

from typing_extensions import override

from crossbench.config import ConfigEnum
from crossbench.probes.probe import Probe, ProbeConfigParser, ProbeContext
from crossbench.probes.result_location import ResultLocation

if TYPE_CHECKING:
  from crossbench import exception
  from crossbench.path import AnyPath
  from crossbench.probes.results import ProbeResult
  from crossbench.runner.run import Run


class HeapType(ConfigEnum):
  JAVA = ("java", "Java Heap")


class DumpHeapProbe(Probe):
  """
  Probe that collects heap dumps.
  """
  NAME: ClassVar = "dump_heap"
  RESULT_LOCATION: ClassVar = ResultLocation.BROWSER

  @classmethod
  @override
  def config_parser(cls) -> ProbeConfigParser[Self]:
    parser = super().config_parser()
    return parser

  @override
  def get_context_cls(self) -> Type[DumpHeapProbeContext]:
    return DumpHeapProbeContext


class DumpHeapProbeContext(ProbeContext[DumpHeapProbe]):

  def __init__(self, probe: DumpHeapProbe, run: Run) -> None:
    super().__init__(probe, run)
    self._results: list[AnyPath] = []

  @override
  def get_default_result_path(self) -> AnyPath:
    dump_dir = super().get_default_result_path()
    self.browser_platform.mkdir(dump_dir)
    return dump_dir

  def start(self) -> None:
    pass

  def stop(self) -> None:
    pass

  @override
  def invoke(self, info_stack: exception.TInfoStack, timeout: dt.timedelta,
             **kwargs) -> None:
    del timeout

    self._dump(info_stack, **kwargs)

  def _dump(self,
            info_stack: exception.TInfoStack,
            type: str,
            identifier: str | None = None,
            suffix: str | None = None,
            **kwargs) -> None:
    self.expect_no_extra_kwargs(kwargs)

    if not suffix:
      suffix = str(dt.datetime.now().strftime("%Y-%m-%d_%H%M%S"))

    label = "_".join(info_stack) + f"_{suffix}"

    match HeapType.parse(type):
      case HeapType.JAVA:
        path = self.result_path / f"{label}.prof"
        if not identifier:
          self.browser.dump_java_heap(path)
        else:
          self.browser_platform.dump_java_heap(identifier, path)
        self._results.append(path)

  @override
  def teardown(self) -> ProbeResult:
    return self.browser_result(file=tuple(self._results))
