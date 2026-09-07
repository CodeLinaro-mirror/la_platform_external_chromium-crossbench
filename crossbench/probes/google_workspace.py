# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, ClassVar, Self

from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing_extensions import override

from crossbench.config import ConfigEnum
from crossbench.probes.probe import Probe, ProbeConfigParser, ProbeContext

if TYPE_CHECKING:
  from crossbench import exception
  from crossbench.probes.results import ProbeResult


class GoogleWorkspaceAction(ConfigEnum):
  COPY_AND_REDIRECT = ("copy_and_redirect",
                       "Copy a template file and redirect to it")


class GoogleWorkspaceProbe(Probe):
  """
  Probe that interacts with the Google Drive API to copy template documents
  into a Shared Drive and redirects the browser to the newly created file.
  """
  NAME: ClassVar = "google_workspace"

  @classmethod
  @override
  def config_parser(cls) -> ProbeConfigParser[Self]:
    parser = super().config_parser()
    return parser

  @override
  def get_context_cls(self) -> type[GoogleWorkspaceProbeContext]:
    return GoogleWorkspaceProbeContext


class GoogleWorkspaceProbeContext(ProbeContext[GoogleWorkspaceProbe]):

  def start(self) -> None:
    pass

  def stop(self) -> None:
    pass

  @override
  def teardown(self) -> ProbeResult:
    return self.empty_result()

  @override
  def invoke(self, info_stack: exception.TInfoStack, timeout: dt.timedelta,
             **kwargs) -> None:
    del info_stack
    del timeout

    action_str = kwargs.pop("action", None)
    action = GoogleWorkspaceAction.parse(action_str)
    if action == GoogleWorkspaceAction.COPY_AND_REDIRECT:
      template_id = kwargs.pop("template_id", None)
      if not template_id:
        raise ValueError("Action 'copy_and_redirect' requires a 'template_id'.")
      self._copy_and_redirect(template_id)
    else:
      raise ValueError(f"GoogleWorkspaceProbe unsupported action: {action}")

    self.expect_no_extra_kwargs(kwargs)

  def _copy_and_redirect(self, template_id: str) -> None:
    secrets = self.run.secrets
    if not secrets or not secrets.google_workspace:
      raise ValueError("Missing google_workspace in secrets.")

    gw_secrets = secrets.google_workspace
    sa_info = gw_secrets.service_account_key
    scopes = ["https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_info(
        sa_info.to_json(), scopes=scopes)

    drive_service = build("drive", "v3", credentials=creds)

    # Copy Document
    body = {
        "name": f"Crossbench-Test-Copy-{template_id}",
        "parents": [gw_secrets.shared_drive_id],
        "appProperties": {
            "crossbench_test": "true",
            "template_id": template_id,
            "ttl":
                (dt.datetime.now(dt.UTC) + dt.timedelta(hours=4)).isoformat()
        }
    }
    copied_file = (
        drive_service.files().copy(
            fileId=template_id,
            body=body,
            supportsAllDrives=True,
            fields="id, webViewLink",
        ).execute())
    new_file_id = copied_file.get("id")
    new_file_link = copied_file.get("webViewLink")

    if not new_file_id:
      raise ValueError(f"Failed to copy Google Workspace file: {copied_file}")

    if not new_file_link:
      raise ValueError(
          f"API response missing webViewLink for file {new_file_id}")

    self.browser.show_url(new_file_link)
