# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from unittest import mock

from crossbench import path as pth
from crossbench.probes.probe_context import EmptyProbeContext
from crossbench.probes.repo_status import RepoStatusProbe
from crossbench.probes.results import EmptyProbeResult
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase
from tests.crossbench.runner.helper import MockRun


class RepoStatusProbeTestCase(CrossbenchFakeFsTestCase):

  def test_probe_name(self) -> None:
    probe = RepoStatusProbe()
    self.assertEqual(probe.name, "cb.repo_status")
    self.assertTrue(probe.is_internal)

  def test_context_teardown(self) -> None:
    probe = RepoStatusProbe()
    run = mock.MagicMock(spec=MockRun)
    context = probe.create_context(run)
    self.assertIsInstance(context, EmptyProbeContext)
    self.assertIsInstance(context.teardown(), EmptyProbeResult)

  def test_setup_creates_patch_diff(self) -> None:
    probe = RepoStatusProbe()
    runner = mock.MagicMock()
    runner.out_dir = pth.LocalPath("/out/dir")
    runner.out_dir.mkdir(parents=True)
    diff_content = "diff --git a/file.py b/file.py\n+new line"

    def mock_sh(*args, stdout=None, **kwargs) -> mock.MagicMock:
      del args, kwargs
      if stdout and hasattr(stdout, "write"):
        stdout.write(diff_content)
      return mock.MagicMock()

    runner.platform.crossbench_details.return_value = {
        "canonical_parent_hash": "abcdef123"
    }
    runner.platform.sh.side_effect = mock_sh

    probe.setup(runner)
    patch_file = runner.out_dir / "patch.diff"
    self.assertTrue(patch_file.exists())
    self.assertEqual(patch_file.read_text(encoding="utf-8"), diff_content)

  def test_setup_skips_no_parent_hash(self) -> None:
    probe = RepoStatusProbe()
    runner = mock.MagicMock()
    runner.out_dir = pth.LocalPath("/out/dir")
    runner.out_dir.mkdir(parents=True)
    runner.platform.crossbench_details.return_value = {}

    probe.setup(runner)
    patch_file = runner.out_dir / "patch.diff"
    self.assertFalse(patch_file.exists())


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
