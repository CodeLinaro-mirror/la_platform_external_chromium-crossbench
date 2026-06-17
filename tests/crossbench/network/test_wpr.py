# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import pathlib
from unittest import mock

from crossbench.network.replay.wpr import LocalWprReplayNetwork
from crossbench.network.traffic_shaping.live import NoTrafficShaper
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase


class WprReplayNetworkTestCase(BaseCrossbenchTestCase):

  def setUp(self):
    super().setUp()
    self.archive_path = pathlib.Path("/wpr/archive.wprgo")
    self.fs.create_file(self.archive_path, st_size=100)
    self.wpr_go_bin = pathlib.Path("/wpr/wpr.go")
    self.fs.create_file(self.wpr_go_bin, st_size=100)
    self.traffic_shaper = NoTrafficShaper(self.platform)

  @mock.patch("crossbench.network.replay.wpr.WprGoFinder.wpr")
  def test_validate_chromium_browser(self, mock_wpr_finder):
    mock_wpr_finder.return_value = self.wpr_go_bin
    network = LocalWprReplayNetwork(
        archive=self.archive_path,
        traffic_shaper=self.traffic_shaper,
        browser_platform=self.platform,
        persist_server=False,
        inject_deterministic_script=False,
        no_archive_certificates=False,
        response_transformations_file=None,
        cross_platform_mode=False,
        host=None)

    browser = mock.Mock()
    browser.attributes().is_chromium_based = True
    # Validation should succeed for chromium browsers
    network.validate(browser)

    # Validation should fail for non-chromium browsers
    browser.attributes().is_chromium_based = False
    with self.assertRaises(ValueError) as cm:
      network.validate(browser)
    self.assertIn("chromium-based browsers are supported", str(cm.exception))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
