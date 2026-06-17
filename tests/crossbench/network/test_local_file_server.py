# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import pathlib
from unittest import mock

from crossbench.network.local_file_server import LocalFileNetwork
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase


class LocalFileNetworkTestCase(BaseCrossbenchTestCase):

  def test_defaults(self):
    path = pathlib.Path("/foo/bar")
    self.fs.create_dir(path)
    network = LocalFileNetwork(path, None, browser_platform=self.platform)
    self.assertTrue(network.is_local_file_server)
    self.assertFalse(network.is_running)

  @mock.patch("crossbench.network.local_file_server."
              "LocalFileNetwork._validate_extra_headers")
  def test_init_validates_headers(self, mock_val):
    path = pathlib.Path("/foo/bar")
    self.fs.create_dir(path)
    LocalFileNetwork(path, None, browser_platform=self.platform)
    mock_val.assert_called_once_with()


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
