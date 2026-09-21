# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from unittest import mock

import google.auth.exceptions

from crossbench.exception import MultiException
from crossbench.pinpoint import auth
from crossbench.pinpoint.exceptions import AuthenticationError, \
    GCloudNotInstalledError
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.mock_helper import ShResult


class AuthTestCase(BaseCrossbenchTestCase):

  def setUp(self):
    super().setUp()
    auth.get_auth_session.cache_clear()
    self.google_auth_default = self.enterContext(
        mock.patch("google.auth.default"))
    self.google_auth_default.side_effect = (
        google.auth.exceptions.DefaultCredentialsError())
    self.ui_prompt = self.enterContext(
        mock.patch("crossbench.cli.ui.ui.prompt"))

  def test_get_auth_session_gcloud_missing(self):
    self.platform.sh_results = []
    # User says "yes" to running gcloud
    self.ui_prompt.return_value = "y"
    # But gcloud is missing (default state in fake fs)

    with self.assertRaises(MultiException) as cm:
      auth.get_auth_session()
    self.assertTrue(cm.exception.matching(GCloudNotInstalledError))

    self.assertNotIn("gcloud", self.platform.sh_cmds)

  def test_get_auth_session_gcloud_present(self):
    self.platform.sh_results = [ShResult("logged in")]
    # User says "yes" to running gcloud
    self.ui_prompt.return_value = "y"

    # gcloud is present
    self.fs.create_file("/usr/bin/gcloud")
    self.platform.set_binary_lookup_override("gcloud", "/usr/bin/gcloud")

    # Second call needs to succeed otherwise we loop
    self.google_auth_default.side_effect = [
        google.auth.exceptions.DefaultCredentialsError(),
        (mock.Mock(), "project_id"),
    ]

    auth.get_auth_session()

    self.assertIn("gcloud", self.platform.sh_cmds[0])

  def test_get_auth_session_prompt_rejected(self):
    self.ui_prompt.return_value = "n"
    self.fs.create_file("/usr/bin/gcloud")
    self.platform.set_binary_lookup_override("gcloud", "/usr/bin/gcloud")

    with self.assertRaises(MultiException) as cm:
      auth.get_auth_session()
    self.assertTrue(cm.exception.matching(AuthenticationError))
    errors = cm.exception.matching(AuthenticationError)
    self.assertIn("gcloud auth application-default login", str(errors[0]))

  def test_get_auth_session_refresh_error(self):
    self.ui_prompt.return_value = "n"
    self.fs.create_file("/usr/bin/gcloud")
    self.platform.set_binary_lookup_override("gcloud", "/usr/bin/gcloud")
    self.google_auth_default.side_effect = (
        google.auth.exceptions.RefreshError("token expired"))

    with self.assertRaises(MultiException) as cm:
      auth.get_auth_session()
    self.assertTrue(cm.exception.matching(AuthenticationError))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
