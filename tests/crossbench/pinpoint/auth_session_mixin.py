# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest
from typing import Final
from unittest import mock

import requests


class MockAuthSessionMixin(unittest.TestCase):
  """Mixin to mock the get_auth_session function."""

  _get_auth_session_patch_target: Final[
      str] = "crossbench.pinpoint.auth.get_auth_session"

  def setUp(self):
    super().setUp()
    self.patcher_get_auth_session = mock.patch(
        self._get_auth_session_patch_target)
    self.mock_get_auth_session = self.patcher_get_auth_session.start()
    self.mock_session = mock.Mock(spec=requests.Session)
    self.mock_get_auth_session.return_value = self.mock_session

  def tearDown(self):
    super().tearDown()
    self.patcher_get_auth_session.stop()
