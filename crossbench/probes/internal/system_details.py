# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast, override

from crossbench.probes.internal.base import (
  InternalJsonResultProbe,
  InternalJsonResultProbeContext,
)

if TYPE_CHECKING:
  from crossbench.runner.actions import Actions
  from crossbench.types import Json


class SystemDetailsProbe(InternalJsonResultProbe):
  """
  Runner-internal meta-probe: Collects the browser's system/platform details.
  """

  NAME: ClassVar = "cb.system.details"
  AUTO_MERGE_REPETITIONS: ClassVar = False

  @override
  def get_context_cls(self) -> type[InternalJsonResultProbeContext]:
    return SystemDetailsProbeContext


class SystemDetailsProbeContext(InternalJsonResultProbeContext):
  @override
  def to_json(self, actions: Actions) -> Json:
    details = dict(self.browser_platform.system_details())
    # The Crossbench checkout lives on the platform that runs Crossbench,
    # which is not necessarily the browser platform (e.g. mobile platforms).
    details["crossbench"] = cast(
      "Json", self.runner.platform.crossbench_details()
    )
    return details
