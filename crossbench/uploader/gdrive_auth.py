# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""OAuth 2.0 user authentication for Google Drive uploads.

Crossbench only requests the narrow 'drive.file' scope, which grants access
to files and folders created by Crossbench itself and nothing else. The first
upload runs an interactive browser consent flow (authorization code with PKCE
and a loopback redirect); the resulting refresh token is cached locally so
subsequent uploads are non-interactive.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import http
import http.server
import json
import logging
import os
import secrets
from typing import Final, override
from urllib import parse as urlparse

import platformdirs
import requests

from crossbench import path as pth
from crossbench import plt
from crossbench.helper import url_helper

_DRIVE_FILE_SCOPE: Final[str] = "https://www.googleapis.com/auth/drive.file"
_AUTH_URI: Final[str] = "https://accounts.google.com/o/oauth2/auth"
_CREDENTIALS_URI: Final[str] = "https://oauth2.googleapis.com/token"

# The "Crossbench Results Upload" Desktop app client, owned by the chromium.org
# Cloud project "kinetic-fire-513913-c4" (its consent screen only lists
# _DRIVE_FILE_SCOPE).
_CLIENT_ID_PREFIX: Final[str] = "268572448152-k97ose9i7s2oh86311eq2thbogvk3hrg"
_CLIENT_ID: Final[str] = f"{_CLIENT_ID_PREFIX}.apps.googleusercontent.com"

# Per Google's OAuth 2.0 docs for installed Desktop apps, the client secret is
# embedded in source and not treated as confidential:
# https://developers.google.com/identity/protocols/oauth2#installed.
_CLIENT_SECRET: Final[str] = "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"  # noqa: S105


class GoogleDriveAuthError(RuntimeError):
  """Raised when Google Drive credentials cannot be obtained."""


class GoogleDriveAuth:
  """Obtains Google Drive access tokens for the 'drive.file' scope."""

  def __init__(self) -> None:
    config_dir = pth.LocalPath(platformdirs.user_config_dir("crossbench"))
    self._token_path: Final[pth.LocalPath] = config_dir / "gdrive_token.json"

  def access_token(self) -> str:
    """Returns a valid access token, running the consent flow if needed."""
    if not (refresh_token := self._load_refresh_token()):
      return self._authorize()
    if token := self._refresh(refresh_token):
      return token
    self._token_path.unlink(missing_ok=True)
    return self._authorize()

  def _load_refresh_token(self) -> str:
    if not self._token_path.is_file():
      return ""
    data = json.loads(self._token_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    refresh_token = data.get("refresh_token")
    assert isinstance(refresh_token, str) and refresh_token
    return refresh_token

  def _store_refresh_token(self, refresh_token: str) -> None:
    self._token_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(self._token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
      json.dump(
        {"refresh_token": refresh_token, "scope": _DRIVE_FILE_SCOPE},
        handle,
        indent=2,
      )

  def _refresh(self, refresh_token: str) -> str:
    """Exchanges a refresh token for an access token, or '' if expired."""
    return self._request_tokens(
      {"refresh_token": refresh_token, "grant_type": "refresh_token"},
      action="token refresh",
      allow_invalid_grant=True,
    )

  def _authorize(self) -> str:
    """Runs the interactive OAuth 2.0 browser consent flow."""
    verifier, challenge = _pkce_pair()
    # Random nonce echoed back on redirect to reject forged local callbacks.
    state = secrets.token_urlsafe(16)

    # Listen on 127.0.0.1:<free_port> for Google's post-consent redirect.
    with _LoopbackServer() as server:
      redirect_uri = server.redirect_uri
      self._open_consent_page(_build_auth_url(redirect_uri, challenge, state))
      params = server.wait_for_redirect()

    code = _extract_auth_code(params, expected_state=state)
    return self._exchange_code(code, verifier, redirect_uri)

  def _open_consent_page(self, auth_url: str) -> None:
    logging.critical("🔐 Waiting for Google Drive authorization.")
    # Skip open_url() on headless hosts (e.g. SSH), where webbrowser.open() can
    # launch blocking terminal text browsers that cannot complete OAuth consent.
    if not plt.PLATFORM.is_headless and plt.PLATFORM.open_url(auth_url):
      logging.info("Authorization URL: %s", auth_url)
      return
    logging.critical("Could not open a browser; visit: %s", auth_url)

  def _exchange_code(self, code: str, verifier: str, redirect_uri: str) -> str:
    return self._request_tokens(
      {
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
      },
      action="token exchange",
    )

  def _request_tokens(
    self,
    data: dict[str, str],
    action: str,
    *,
    allow_invalid_grant: bool = False,
  ) -> str:
    """POSTs to the OAuth token endpoint, caches any refresh_token, and returns
    the access_token (or '' on HTTP 400/401 when allow_invalid_grant is True).
    """
    try:
      response = requests.post(
        _CREDENTIALS_URI,
        data={"client_id": _CLIENT_ID, "client_secret": _CLIENT_SECRET, **data},
        timeout=url_helper.DEFAULT_REQUEST_TIMEOUT.total_seconds(),
      )
    except requests.RequestException as e:
      raise GoogleDriveAuthError(f"OAuth {action} failed: {e}") from e
    if allow_invalid_grant and response.status_code in (400, 401):
      return ""
    if not response.ok:
      status = response.status_code
      detail = " ".join(response.text.split())
      raise GoogleDriveAuthError(f"OAuth {action} HTTP {status}: {detail}")
    tokens = response.json()
    assert isinstance(tokens, dict)
    refresh_token = tokens.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token:
      self._store_refresh_token(refresh_token)
    access_token = tokens.get("access_token")
    assert isinstance(access_token, str) and access_token
    return access_token


class _LoopbackServer(http.server.HTTPServer):
  """Minimal local HTTP server that captures a single OAuth redirect."""

  def __init__(self) -> None:
    super().__init__(("127.0.0.1", 0), _LoopbackRequestHandler)
    self.params: dict[str, str] = {}

  @property
  def redirect_uri(self) -> str:
    return f"http://127.0.0.1:{self.server_port}/"

  def wait_for_redirect(self) -> dict[str, str]:
    """Blocks until the redirect arrives, returning its query parameters."""
    while not self.params:
      self.handle_request()
    return self.params


class _LoopbackRequestHandler(http.server.BaseHTTPRequestHandler):
  """Handles the single OAuth redirect arriving on 127.0.0.1."""

  def do_GET(self) -> None:  # noqa: N802
    assert isinstance(self.server, _LoopbackServer)
    parsed = urlparse.urlparse(self.path)
    if parsed.path != "/":
      self.send_error(http.HTTPStatus.NOT_FOUND)
      return
    params = dict(urlparse.parse_qsl(parsed.query))
    if "code" not in params and "error" not in params:
      self.send_error(http.HTTPStatus.BAD_REQUEST)
      return
    body = (
      "<h2>Crossbench: Google Drive authorization received.</h2>"
      "<p>You can close this tab.</p>"
    )
    if "error" in params or not params.get("code"):
      body = "<h2>Crossbench: authorization failed.</h2>"
    self.server.params = params
    with contextlib.suppress(OSError):
      self.send_response(http.HTTPStatus.OK)
      self.send_header("Content-Type", "text/html; charset=utf-8")
      self.end_headers()
      self.wfile.write(body.encode("utf-8"))

  @override
  def log_message(self, format: str, *args: object) -> None:
    del format, args


def _pkce_pair() -> tuple[str, str]:
  """Generates a PKCE (verifier, S256 challenge) pair (RFC 7636).

  The browser URL only carries the SHA-256 challenge; sending the secret
  verifier during token exchange proves the caller initiated the flow.
  """
  verifier = secrets.token_urlsafe(64)
  digest = hashlib.sha256(verifier.encode("ascii")).digest()
  challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
  return verifier, challenge


def _build_auth_url(redirect_uri: str, challenge: str, state: str) -> str:
  """Builds the Google OAuth 2.0 consent URL."""
  query = urlparse.urlencode(
    {
      "client_id": _CLIENT_ID,
      "redirect_uri": redirect_uri,
      "response_type": "code",
      "scope": _DRIVE_FILE_SCOPE,
      "code_challenge": challenge,
      "code_challenge_method": "S256",
      "state": state,
      # Request a reusable refresh_token alongside the short-lived access_token.
      "access_type": "offline",
      "prompt": "consent",
    }
  )
  return f"{_AUTH_URI}?{query}"


def _extract_auth_code(params: dict[str, str], expected_state: str) -> str:
  """Validates the OAuth redirect parameters and returns the auth code."""
  if error := params.get("error"):
    raise GoogleDriveAuthError(f"Authorization failed: {error}")
  if params.get("state") != expected_state:
    raise GoogleDriveAuthError("Authorization failed: state mismatch.")
  if not (code := params.get("code")):
    raise GoogleDriveAuthError("Authorization failed: missing code.")
  return code
