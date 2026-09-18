# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

AUTH_ERROR_MESSAGE = ("Authentication failed or expired. Please run:\n"
                      "  gcloud auth application-default login\n"
                      "to configure your credentials.")


class GCloudNotInstalledError(Exception):
  pass


class AuthenticationError(Exception):

  def __init__(self, message: str = AUTH_ERROR_MESSAGE) -> None:
    super().__init__(message)
