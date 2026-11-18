# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final, override
from unittest import mock

import requests

from crossbench.uploader.gdrive import GoogleDriveUploader
from crossbench.uploader.gdrive_auth import (
  GoogleDriveAuth,
  GoogleDriveAuthError,
)
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase

if TYPE_CHECKING:
  from collections.abc import Sequence

_SESSION_URI: Final[str] = "https://www.googleapis.com/upload/session-123"
_NON_TARGETS: Final = (
  "gdrive://",
  "gdrive://root",
  "gdrive://1AbC-dEf_GhI",
  "https://drive.google.com/drive/folders/1AbC-dEf_GhI",
  "gs://bucket/path",
  "https://unsupported-bucket/path",
  "drive",
)


def _mock_response(
  status_code: int,
  payload: dict[str, object] | None = None,
  headers: dict[str, str] | None = None,
) -> mock.MagicMock:
  response = mock.MagicMock(spec=requests.Response)
  response.status_code = status_code
  response.ok = 200 <= status_code < 300
  body = {} if payload is None else payload
  response.json.return_value = body
  response.text = json.dumps(body)
  response.headers = {} if headers is None else headers
  return response


class GoogleDriveUploaderTestCase(BaseCrossbenchTestCase):
  @override
  def setUp(self) -> None:
    super().setUp()
    self.out_dir.mkdir()
    self.test_file = self.out_dir / "test_uuid.tar.gz"
    self.test_file.write_text("data", encoding="utf-8")
    self.mock_access_token = self.enterContext(
      mock.patch.object(GoogleDriveAuth, "access_token", return_value="TOKEN")
    )

  def test_parse_target_valid(self) -> None:
    for target in ("gdrive", "  gdrive "):
      with self.subTest(target=target):
        self.assertEqual(GoogleDriveUploader.parse_target(target), "gdrive")

  def test_parse_target_other_target_ignored(self) -> None:
    for target in _NON_TARGETS:
      with self.subTest(target=target):
        self.assertEqual(GoogleDriveUploader.parse_target(target), "")

  def test_invalid_url(self) -> None:
    with self.assertRaises(AssertionError):
      GoogleDriveUploader("gdrive://1AbC-dEf_GhI")

  def _upload(
    self, responses: Sequence[mock.MagicMock]
  ) -> tuple[str, mock.MagicMock]:
    """Runs upload() with requests.Session.request mocked."""
    captured_auth_headers: list[str] = []
    it = iter(responses)

    def fake_request(
      session: requests.Session, method: str, url: str, **kwargs: object
    ) -> mock.MagicMock:
      del method, url, kwargs
      captured_auth_headers.append(str(session.headers.get("Authorization")))
      return next(it)

    with mock.patch.object(
      requests.Session, "request", autospec=True, side_effect=fake_request
    ) as mock_request:
      url = GoogleDriveUploader("gdrive").upload(self.test_file)
    self.assertTrue(all(h == "Bearer TOKEN" for h in captured_auth_headers))
    return url, mock_request

  def test_upload_folder_exists(self) -> None:
    url, mock_request = self._upload(
      [
        _mock_response(200, {"files": [{"id": "EXISTING_FOLDER"}]}),
        _mock_response(200, headers={"location": _SESSION_URI}),
        _mock_response(
          200, {"webViewLink": "https://drive.google.com/file/d/FILE_ID/view"}
        ),
      ]
    )

    self.assertEqual(url, "https://drive.google.com/file/d/FILE_ID/view")
    self.mock_access_token.assert_called_once_with()
    self.assertEqual(mock_request.call_count, 3)
    lookup_call, init_call, put_call = mock_request.call_args_list

    self.assertEqual(lookup_call.args[1], "GET")
    query = lookup_call.kwargs["params"]["q"]
    self.assertIn("name = 'crossbench-results'", query)
    self.assertIn("'root' in parents", query)
    self.assertIn("trashed = false", query)

    self.assertEqual(init_call.args[1], "POST")
    self.assertIn("uploadType=resumable", init_call.args[2])
    metadata = json.loads(init_call.kwargs["data"].decode("utf-8"))
    self.assertEqual(
      metadata,
      {"name": "test_uuid.tar.gz", "parents": ["EXISTING_FOLDER"]},
    )
    self.assertEqual(
      init_call.kwargs["headers"]["x-upload-content-type"], "application/gzip"
    )

    self.assertEqual(put_call.args[1:3], ("PUT", _SESSION_URI))
    self.assertEqual(put_call.kwargs["data"], b"data")

  def test_upload_folder_created(self) -> None:
    url, mock_request = self._upload(
      [
        _mock_response(200, {"files": []}),
        _mock_response(200, {"id": "NEW_FOLDER"}),
        _mock_response(200, headers={"location": _SESSION_URI}),
        _mock_response(
          200, {"webViewLink": "https://drive.google.com/file/d/FILE_ID/view"}
        ),
      ]
    )

    self.assertEqual(url, "https://drive.google.com/file/d/FILE_ID/view")
    self.assertEqual(mock_request.call_count, 4)
    _, create_call, init_call, _ = mock_request.call_args_list
    self.assertEqual(
      create_call.kwargs["json"],
      {
        "name": "crossbench-results",
        "mimeType": "application/vnd.google-apps.folder",
        "parents": ["root"],
      },
    )
    metadata = json.loads(init_call.kwargs["data"].decode("utf-8"))
    self.assertEqual(metadata["parents"], ["NEW_FOLDER"])

  def test_upload_multi_chunk(self) -> None:
    chunk_bytes = 16 * 1024 * 1024
    self.test_file.write_bytes(b"x" * (chunk_bytes + 10))
    url, mock_request = self._upload(
      [
        _mock_response(200, {"files": [{"id": "F"}]}),
        _mock_response(200, headers={"location": _SESSION_URI}),
        _mock_response(308, headers={"range": f"bytes=0-{chunk_bytes - 1}"}),
        _mock_response(
          200, {"webViewLink": "https://drive.google.com/file/d/BIG/view"}
        ),
      ]
    )
    self.assertEqual(url, "https://drive.google.com/file/d/BIG/view")
    self.assertEqual(mock_request.call_count, 4)

  def test_upload_auth_failure(self) -> None:
    self.mock_access_token.side_effect = GoogleDriveAuthError("no consent")
    with (
      mock.patch.object(requests.Session, "request") as mock_request,
      self.assertRaises(RuntimeError) as cm,
    ):
      GoogleDriveUploader("gdrive").upload(self.test_file)
    self.assertIn("no consent", str(cm.exception))
    mock_request.assert_not_called()

  def test_upload_folder_lookup_failure(self) -> None:
    with self.assertRaises(RuntimeError) as cm:
      self._upload([_mock_response(403, {"error": "insufficient scopes"})])
    self.assertIn("folder lookup HTTP 403", str(cm.exception))
    self.assertIn("insufficient scopes", str(cm.exception))

  def test_upload_folder_creation_failure(self) -> None:
    with self.assertRaises(RuntimeError) as cm:
      self._upload(
        [
          _mock_response(200, {"files": []}),
          _mock_response(500, {"error": "backend error"}),
        ]
      )
    self.assertIn("folder creation HTTP 500", str(cm.exception))
    self.assertIn("backend error", str(cm.exception))

  def test_upload_failure(self) -> None:
    with self.assertRaises(RuntimeError) as cm:
      self._upload(
        [
          _mock_response(200, {"files": [{"id": "F"}]}),
          _mock_response(200, headers={"location": _SESSION_URI}),
          _mock_response(403, {"error": "storageQuotaExceeded"}),
        ]
      )
    self.assertIn("upload HTTP 403", str(cm.exception))
    self.assertIn("storageQuotaExceeded", str(cm.exception))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
