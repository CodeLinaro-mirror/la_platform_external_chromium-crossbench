# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
from unittest import mock

from crossbench.probes.google_workspace import GoogleWorkspaceProbe
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


class GoogleWorkspaceProbeTestCase(CrossbenchFakeFsTestCase):

  def test_parse_default(self):
    probe = GoogleWorkspaceProbe.config_parser().parse({})
    self.assertIsInstance(probe, GoogleWorkspaceProbe)
    self.assertEqual(probe.name, "google_workspace")

  @mock.patch("crossbench.probes.google_workspace.service_account.Credentials"
              ".from_service_account_info")
  @mock.patch("crossbench.probes.google_workspace.build")
  def test_copy_and_redirect(self, mock_build, mock_creds_info):
    # Mock drive service
    mock_files = mock.MagicMock()
    mock_drive = mock.MagicMock()
    mock_drive.files.return_value = mock_files
    mock_build.return_value = mock_drive

    # Mock file copy response
    mock_copy = mock.MagicMock()
    mock_copy.execute.return_value = {
        "id": "new_file_id",
        "webViewLink": "https://docs.google.com/document/d/new_file_id/edit"
    }
    mock_files.copy.return_value = mock_copy

    probe = GoogleWorkspaceProbe.config_parser().parse({})

    # Mock Run and Secrets
    run = mock.MagicMock()
    mock_gw_secrets = mock.MagicMock()
    mock_sa = mock.MagicMock()
    mock_sa.to_json.return_value = {"project_id": "test-project"}
    mock_gw_secrets.service_account_key = mock_sa
    mock_gw_secrets.shared_drive_id = "test_drive_id"
    run.secrets.google_workspace = mock_gw_secrets

    context = probe.create_context(run)
    context.invoke(
        info_stack=("step",),
        timeout=dt.timedelta(seconds=1),
        action="copy_and_redirect",
        template_id="magic_template")

    # Assert API interactions
    mock_build.assert_called_once_with("drive", "v3", credentials=mock.ANY)
    mock_files.copy.assert_called_once_with(
        fileId="magic_template",
        body={
            "name": "Crossbench-Test-Copy-magic_template",
            "parents": ["test_drive_id"],
            "appProperties": {
                "crossbench_test": "true",
                "template_id": "magic_template",
                "ttl": mock.ANY
            }
        },
        supportsAllDrives=True,
        fields="id, webViewLink")

    # Assert browser interaction
    # type: ignore[attr-defined]
    context.browser.show_url.assert_called_once_with(
        "https://docs.google.com/document/d/new_file_id/edit")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
