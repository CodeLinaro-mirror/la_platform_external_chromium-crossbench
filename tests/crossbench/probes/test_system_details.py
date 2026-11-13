# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from unittest import mock

from crossbench import __version__
from crossbench.plt.base import Platform
from crossbench.probes.internal.system_details import (
  SystemDetailsProbe,
  SystemDetailsProbeContext,
)
from tests import test_helper
from tests.crossbench.mock_helper import RemoteLinuxMockPlatform
from tests.crossbench.runner.helper import BaseRunnerTestCase


class SystemDetailsProbeTestCase(BaseRunnerTestCase):
  def test_crossbench_details_come_from_runner_platform(self) -> None:
    # The mock run's browser platform is a remote MagicMock.
    run = self.mock_run()
    device_details = {"machine": "arm64"}
    crossbench_details = {"version": __version__, "current_hash": "f00dbab"}
    context = SystemDetailsProbeContext(SystemDetailsProbe(), run)
    with (
      mock.patch.object(
        run.browser.platform, "system_details", return_value=device_details
      ),
      mock.patch.object(
        run.runner.platform,
        "crossbench_details",
        return_value=crossbench_details,
      ),
    ):
      details = context.to_json(mock.MagicMock())

    self.assertEqual(
      details,
      {
        "machine": "arm64",
        "crossbench": crossbench_details,
      },
    )
    # The browser platform's (cached) details are not modified.
    self.assertEqual(device_details, {"machine": "arm64"})

  def test_remote_browser_platform_has_crossbench_details(self) -> None:
    # Uses the production system_details() instead of the mock's canned one,
    # except for the details that would run shell commands.
    self.mock_platform_default_tmp_dir(RemoteLinuxMockPlatform)
    remote_platform = RemoteLinuxMockPlatform(self.platform)
    run = self.mock_run()
    context = SystemDetailsProbeContext(SystemDetailsProbe(), run)
    with (
      mock.patch.object(run.browser, "platform", remote_platform),
      mock.patch.object(run.runner, "platform", self.platform),
      mock.patch.multiple(
        remote_platform,
        python_details=mock.DEFAULT,
        display_details=mock.DEFAULT,
      ),
      mock.patch.object(
        RemoteLinuxMockPlatform,
        "system_details",
        Platform.system_details.__wrapped__,
      ),
    ):
      details = context.to_json(mock.MagicMock())

    assert isinstance(details, dict)
    self.assertEqual(details["machine"], str(remote_platform.machine))
    self.assertEqual(details["crossbench"], self.platform.crossbench_details())


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
