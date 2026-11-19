# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import hashlib
import json
import logging
import stat
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Final, override
from unittest import mock

import requests

from crossbench.uploader.gdrive_auth import (
  GoogleDriveAuth,
  GoogleDriveAuthError,
)
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase

if TYPE_CHECKING:
  from collections.abc import Sequence

_EXPECTED_SCOPE: Final[str] = "https://www.googleapis.com/auth/drive.file"


def _token_response(status_code: int, payload: object = None) -> mock.MagicMock:
  response = mock.MagicMock(spec=requests.Response)
  response.status_code = status_code
  response.ok = 200 <= status_code < 300
  body = {} if payload is None else payload
  response.json.return_value = body
  response.text = json.dumps(body)
  return response


def _spawn_redirect_client(
  redirect_uri: str,
  query: str,
  pre_requests: tuple[str, ...],
  errors: list[BaseException],
) -> threading.Thread:
  base_uri = redirect_uri.rstrip("/")
  final_url = f"{redirect_uri}?{query}"

  def follow_redirect() -> None:
    try:
      for rel_path in pre_requests:
        try:
          with urllib.request.urlopen(
            f"{base_uri}{rel_path}", timeout=5
          ) as resp:
            resp.read()
        except urllib.error.HTTPError:
          pass
      with urllib.request.urlopen(final_url, timeout=5) as response:
        response.read()
    except BaseException as exc:  # pragma: no cover
      errors.append(exc)

  thread = threading.Thread(target=follow_redirect, daemon=True)
  thread.start()
  return thread


class _HeadlessUrlRedirectHandler(logging.Handler):
  """Extracts the logged OAuth consent URL and simulates visiting it."""

  def __init__(self) -> None:
    super().__init__(level=logging.CRITICAL)
    self.messages: list[str] = []
    self.thread: threading.Thread | None = None
    self.errors: list[BaseException] = []

  @override
  def emit(self, record: logging.LogRecord) -> None:
    msg = self.format(record)
    self.messages.append(msg)
    if "https://accounts.google.com/" not in msg or self.thread is not None:
      return
    auth_url = "https://" + msg.split("https://", 1)[1].strip()
    params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(auth_url).query))
    self.thread = _spawn_redirect_client(
      params["redirect_uri"],
      f"code=AUTH_CODE&state={params['state']}",
      pre_requests=(),
      errors=self.errors,
    )


class GoogleDriveAuthTestCase(BaseCrossbenchTestCase):
  @override
  def setUp(self) -> None:
    super().setUp()
    self.config_dir = self.out_dir / "config"
    self.mock_user_config_dir = self.enterContext(
      mock.patch(
        "platformdirs.user_config_dir", return_value=str(self.config_dir)
      )
    )
    self.token_path = self.config_dir / "gdrive_token.json"
    self.auth = GoogleDriveAuth()

  def _write_token(self, refresh_token: object = "REFRESH") -> None:
    self.token_path.parent.mkdir(parents=True, exist_ok=True)
    self.token_path.write_text(
      json.dumps({"refresh_token": refresh_token}), encoding="utf-8"
    )

  def _run_consent(
    self,
    redirect_query: str,
    post_responses: Sequence[mock.MagicMock | Exception],
    *,
    pre_requests: tuple[str, ...] = (),
    open_url_result: bool = True,
  ) -> tuple[str, dict[str, str], mock.Mock]:
    """Runs access_token() through the interactive loopback consent flow."""
    captured_auth_params: dict[str, str] = {}
    redirect_thread: threading.Thread | None = None
    thread_errors: list[BaseException] = []

    def fake_open_url(auth_url: str) -> bool:
      nonlocal redirect_thread
      params = dict(
        urllib.parse.parse_qsl(urllib.parse.urlparse(auth_url).query)
      )
      captured_auth_params.update(params)
      redirect_thread = _spawn_redirect_client(
        params["redirect_uri"],
        redirect_query.format(state=params["state"]),
        pre_requests=pre_requests,
        errors=thread_errors,
      )
      return open_url_result

    try:
      with (
        mock.patch.object(self.platform, "open_url", side_effect=fake_open_url),
        mock.patch(
          "crossbench.uploader.gdrive_auth.requests.post",
          side_effect=list(post_responses),
        ) as mock_post,
      ):
        token = self.auth.access_token()
    finally:
      if redirect_thread is not None:
        redirect_thread.join(timeout=5)
    if thread_errors:
      raise thread_errors[0]
    return token, captured_auth_params, mock_post

  def test_uses_crossbench_user_config_dir(self) -> None:
    self.mock_user_config_dir.assert_called_once_with("crossbench")

  def test_access_token_refresh(self) -> None:
    self._write_token("REFRESH")
    refresh_response = _token_response(200, {"access_token": "ACCESS"})
    with (
      mock.patch(
        "crossbench.uploader.gdrive_auth.requests.post",
        return_value=refresh_response,
      ) as mock_post,
      mock.patch.object(self.platform, "open_url") as mock_open_url,
    ):
      self.assertEqual(self.auth.access_token(), "ACCESS")
    mock_open_url.assert_not_called()
    mock_post.assert_called_once()
    data = mock_post.call_args.kwargs["data"]
    self.assertEqual(data["refresh_token"], "REFRESH")
    self.assertEqual(data["grant_type"], "refresh_token")
    self.assertTrue(data["client_id"].endswith(".apps.googleusercontent.com"))
    self.assertTrue(data["client_secret"])

  def test_access_token_refresh_rotates_refresh_token(self) -> None:
    self._write_token("OLD_REFRESH")
    refresh_response = _token_response(
      200, {"access_token": "ACCESS", "refresh_token": "NEW_REFRESH"}
    )
    with mock.patch(
      "crossbench.uploader.gdrive_auth.requests.post",
      return_value=refresh_response,
    ):
      self.assertEqual(self.auth.access_token(), "ACCESS")
    cached = json.loads(self.token_path.read_text(encoding="utf-8"))
    self.assertEqual(cached["refresh_token"], "NEW_REFRESH")

  def test_access_token_refresh_invalid_grant_reauthorizes(self) -> None:
    self._write_token("STALE")
    token, _, mock_post = self._run_consent(
      "code=AUTH_CODE&state={state}",
      [
        _token_response(400, {"error": "invalid_grant"}),
        _token_response(200, {"access_token": "FRESH"}),
      ],
    )
    self.assertEqual(token, "FRESH")
    self.assertEqual(mock_post.call_count, 2)
    self.assertFalse(self.token_path.exists())

  def test_access_token_refresh_server_error_preserves_cached_token(
    self,
  ) -> None:
    self._write_token("VALID_REFRESH")
    refresh_response = _token_response(503, {"error": "backend_unavailable"})
    with (
      mock.patch(
        "crossbench.uploader.gdrive_auth.requests.post",
        return_value=refresh_response,
      ),
      mock.patch.object(self.platform, "open_url") as mock_open_url,
      self.assertRaises(GoogleDriveAuthError) as cm,
    ):
      self.auth.access_token()
    self.assertIn("503", str(cm.exception))
    mock_open_url.assert_not_called()
    self.assertTrue(self.token_path.exists())

  def test_access_token_refresh_network_error_preserves_cached_token(
    self,
  ) -> None:
    self._write_token("VALID_REFRESH")
    with (
      mock.patch(
        "crossbench.uploader.gdrive_auth.requests.post",
        side_effect=requests.ConnectionError("offline"),
      ),
      mock.patch.object(self.platform, "open_url") as mock_open_url,
      self.assertRaises(GoogleDriveAuthError) as cm,
    ):
      self.auth.access_token()
    self.assertIn("offline", str(cm.exception))
    mock_open_url.assert_not_called()
    self.assertTrue(self.token_path.exists())

  def test_access_token_empty_cached_token_asserts(self) -> None:
    self._write_token("")
    with (
      mock.patch.object(self.platform, "open_url") as mock_open_url,
      self.assertRaises(AssertionError),
    ):
      self.auth.access_token()
    mock_open_url.assert_not_called()

  def test_authorize_pkce_and_token_exchange_request(self) -> None:
    token_response = _token_response(
      200, {"access_token": "ACCESS", "refresh_token": "REFRESH"}
    )
    token, auth_params, mock_post = self._run_consent(
      "code=AUTH_CODE&state={state}", [token_response]
    )
    self.assertEqual(token, "ACCESS")
    self.assertTrue(
      auth_params["client_id"].endswith(".apps.googleusercontent.com")
    )
    self.assertEqual(auth_params["scope"], _EXPECTED_SCOPE)
    self.assertEqual(auth_params["response_type"], "code")
    self.assertEqual(auth_params["code_challenge_method"], "S256")
    self.assertEqual(auth_params["access_type"], "offline")
    self.assertEqual(auth_params["prompt"], "consent")
    self.assertTrue(auth_params["redirect_uri"].startswith("http://127.0.0.1:"))

    mock_post.assert_called_once()
    data = mock_post.call_args.kwargs["data"]
    self.assertEqual(data["code"], "AUTH_CODE")
    self.assertEqual(data["client_id"], auth_params["client_id"])
    self.assertTrue(data["client_secret"])
    self.assertEqual(data["grant_type"], "authorization_code")
    self.assertEqual(data["redirect_uri"], auth_params["redirect_uri"])
    expected_challenge = (
      base64.urlsafe_b64encode(
        hashlib.sha256(data["code_verifier"].encode("ascii")).digest()
      )
      .rstrip(b"=")
      .decode("ascii")
    )
    self.assertEqual(auth_params["code_challenge"], expected_challenge)

  def test_authorize_caches_refresh_token_with_0600_mode(self) -> None:
    token_response = _token_response(
      200, {"access_token": "ACCESS", "refresh_token": "REFRESH"}
    )
    self._run_consent("code=AUTH_CODE&state={state}", [token_response])
    cached = json.loads(self.token_path.read_text(encoding="utf-8"))
    self.assertEqual(
      cached,
      {
        "refresh_token": "REFRESH",
        "scope": _EXPECTED_SCOPE,
      },
    )
    mode = stat.S_IMODE(self.token_path.stat().st_mode)
    self.assertEqual(mode, 0o600)

  def test_authorize_ignores_favicon_and_bare_probe_requests(self) -> None:
    token_response = _token_response(200, {"access_token": "ACCESS"})
    token, _, _ = self._run_consent(
      "code=AUTH_CODE&state={state}",
      [token_response],
      pre_requests=("/favicon.ico", "/"),
    )
    self.assertEqual(token, "ACCESS")

  def test_authorize_user_denied(self) -> None:
    with self.assertRaises(GoogleDriveAuthError) as cm:
      self._run_consent(
        "error=access_denied&state={state}", [_token_response(200, {})]
      )
    self.assertIn("access_denied", str(cm.exception))

  def test_authorize_state_mismatch(self) -> None:
    with self.assertRaises(GoogleDriveAuthError) as cm:
      self._run_consent(
        "code=AUTH_CODE&state=WRONG", [_token_response(200, {})]
      )
    self.assertIn("state mismatch", str(cm.exception))

  def test_authorize_token_exchange_http_failure(self) -> None:
    token_response = _token_response(400, {"error": "invalid_grant"})
    with self.assertRaises(GoogleDriveAuthError) as cm:
      self._run_consent("code=AUTH_CODE&state={state}", [token_response])
    self.assertIn("400", str(cm.exception))
    self.assertIn("invalid_grant", str(cm.exception))

  def test_authorize_browser_launch_failure_logs_url_and_completes(
    self,
  ) -> None:
    """When open_url() returns False, the URL is logged and consent succeeds."""
    token_response = _token_response(200, {"access_token": "ACCESS"})
    with self.assertLogs(level="CRITICAL") as logs:
      token, _, _ = self._run_consent(
        "code=AUTH_CODE&state={state}",
        [token_response],
        open_url_result=False,
      )
    self.assertEqual(token, "ACCESS")
    self.assertTrue(
      any("Could not open a browser" in line for line in logs.output)
    )
    self.assertTrue(any("accounts.google.com" in line for line in logs.output))

  def test_authorize_headless_skips_browser_launch_and_completes(self) -> None:
    """Headless hosts skip open_url() and complete via the logged URL."""
    handler = _HeadlessUrlRedirectHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    self.addCleanup(root_logger.removeHandler, handler)

    try:
      with (
        mock.patch.object(
          type(self.platform),
          "is_headless",
          new_callable=mock.PropertyMock,
          return_value=True,
        ),
        mock.patch.object(self.platform, "open_url") as mock_open_url,
        mock.patch(
          "crossbench.uploader.gdrive_auth.requests.post",
          return_value=_token_response(200, {"access_token": "ACCESS"}),
        ),
      ):
        self.assertEqual(self.auth.access_token(), "ACCESS")
    finally:
      if handler.thread is not None:
        handler.thread.join(timeout=5)
    if handler.errors:
      raise handler.errors[0]
    mock_open_url.assert_not_called()
    self.assertTrue(
      any("Could not open a browser" in msg for msg in handler.messages)
    )


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
