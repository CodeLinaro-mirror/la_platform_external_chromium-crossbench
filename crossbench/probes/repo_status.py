# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from typing_extensions import override

from crossbench import path as pth
from crossbench.probes.internal.base import InternalProbe
from crossbench.probes.probe_context import EmptyProbeContext

if TYPE_CHECKING:
  from crossbench.runner.run import Run
  from crossbench.runner.runner import Runner


class RepoStatusProbe(InternalProbe):
  """Probe that generates a git patch diff of repository modifications."""
  NAME: ClassVar[str] = "cb.repo_status"

  @override
  def validate_result(self, run: Run) -> None:
    pass

  @override
  def get_context_cls(self) -> type[EmptyProbeContext[RepoStatusProbe]]:
    return EmptyProbeContext

  @override
  def setup(self, runner: Runner) -> None:
    super().setup(runner)
    details = runner.platform.crossbench_details()
    if not (canonical_parent_hash := details.get("canonical_parent_hash")):
      return
    patch_file = runner.out_dir / "patch.diff"
    try:
      with patch_file.open("w", encoding="utf-8") as f:
        runner.platform.sh(
            "git",
            "diff",
            canonical_parent_hash,
            stdout=f,
            cwd=pth.ROOT_DIR,
            check=False)
    except (RuntimeError, ValueError, OSError) as e:
      logging.warning("Failed to generate git patch: %s", e)
