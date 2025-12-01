# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest
from unittest import mock


class MockRequestsMixin(unittest.TestCase):
  """Mixin to mock the requests.get and requests.post functions."""

  def setUp(self):
    super().setUp()
    self.mock_get = self.enterContext(
        mock.patch("crossbench.pinpoint.requests.get"))
    self.mock_post = self.enterContext(
        mock.patch("crossbench.pinpoint.requests.post"))
