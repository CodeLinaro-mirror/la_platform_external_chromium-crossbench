# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final, override

import requests
from google import resumable_media
from google.resumable_media.requests import ResumableUpload

from crossbench.helper import url_helper
from crossbench.uploader.base import BaseUploader
from crossbench.uploader.gdrive_auth import GoogleDriveAuth

if TYPE_CHECKING:
  from crossbench import path as pth

_TARGET: Final[str] = "gdrive"
_FOLDER_NAME: Final[str] = "crossbench-results"

_FILES_ENDPOINT: Final[str] = "https://www.googleapis.com/drive/v3/files"
_UPLOAD_URL: Final[str] = (
  "https://www.googleapis.com/upload/drive/v3/files"
  "?uploadType=resumable&fields=webViewLink"
)
_FOLDER_MIME_TYPE: Final[str] = "application/vnd.google-apps.folder"
_UPLOAD_CHUNK_BYTES: Final[int] = 16 * 1024 * 1024


class GoogleDriveUploader(BaseUploader):
  """Uploads files into a 'crossbench-results' folder in Google Drive.

  Only the narrow 'drive.file' OAuth scope is requested, so Crossbench can
  only see and modify files and folders that it created itself. This is also
  why uploading into arbitrary, user-created folders is not supported.
  """

  TARGET_FORMATS: ClassVar[tuple[str, ...]] = (
    f"{_TARGET} (My Drive/{_FOLDER_NAME}/)",
  )

  def __init__(self, url: str) -> None:
    super().__init__(url)
    assert self._url == _TARGET, f"Not a Google Drive target: {url!r}"

  @classmethod
  @override
  def parse_target(cls, target: str) -> str:
    if target.strip() == _TARGET:
      return _TARGET
    return ""

  @override
  def upload(self, file_path: pth.LocalPath) -> str:
    token = GoogleDriveAuth().access_token()
    with requests.Session() as session:
      session.headers["Authorization"] = f"Bearer {token}"
      folder_id = self._find_or_create_folder(session)
      return self._upload_file(session, file_path, folder_id)

  def _upload_file(
    self,
    session: requests.Session,
    file_path: pth.LocalPath,
    folder_id: str,
  ) -> str:
    upload = ResumableUpload(_UPLOAD_URL, chunk_size=_UPLOAD_CHUNK_BYTES)
    metadata = {"name": file_path.name, "parents": [folder_id]}
    try:
      with file_path.open("rb") as stream:
        upload.initiate(session, stream, metadata, "application/gzip")
        response: requests.Response | None = None
        while not upload.finished:
          response = upload.transmit_next_chunk(session)
    except resumable_media.InvalidResponse as e:
      _check_response(e.response, "upload")
      raise RuntimeError(f"Google Drive upload failed: {e}") from e
    assert response is not None
    return str(response.json()["webViewLink"])

  def _find_or_create_folder(self, session: requests.Session) -> str:
    """Returns the results folder ID in My Drive, creating it if needed."""
    timeout = url_helper.DEFAULT_REQUEST_TIMEOUT.total_seconds()
    # With 'drive.file', this only lists folders created by Crossbench itself.
    query = (
      f"name = '{_FOLDER_NAME}' and "
      f"mimeType = '{_FOLDER_MIME_TYPE}' and "
      "'root' in parents and trashed = false"
    )
    response = session.get(
      _FILES_ENDPOINT,
      params={"q": query, "spaces": "drive", "fields": "files(id)"},
      timeout=timeout,
    )
    _check_response(response, "folder lookup")
    if files := response.json().get("files"):
      return str(files[0]["id"])

    response = session.post(
      _FILES_ENDPOINT,
      params={"fields": "id"},
      json={
        "name": _FOLDER_NAME,
        "mimeType": _FOLDER_MIME_TYPE,
        "parents": ["root"],
      },
      timeout=timeout,
    )
    _check_response(response, "folder creation")
    return str(response.json()["id"])


def _check_response(response: requests.Response, action: str) -> None:
  if response.ok:
    return
  status = response.status_code
  detail = " ".join(response.text.split())
  raise RuntimeError(f"Google Drive {action} HTTP {status}: {detail}")
