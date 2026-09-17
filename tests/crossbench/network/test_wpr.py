# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import argparse
import pathlib
from typing import Any
from unittest import mock

from crossbench.cli.config.network import NetworkConfig, NetworkType
from crossbench.network.replay.wpr import LocalWprReplayNetwork
from crossbench.network.traffic_shaping.live import NoTrafficShaper
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase


class WprReplayNetworkTestCase(BaseCrossbenchTestCase):

  def setUp(self):
    super().setUp()
    self.archive_path = pathlib.Path("/wpr/archive.wprgo")
    self.fs.create_file(
        self.archive_path, contents=b"dummy wpr archive content")
    self.wpr_go_bin = pathlib.Path("/wpr/wpr.go")
    self.fs.create_file(self.wpr_go_bin, contents=b"dummy wpr binary")
    self.traffic_shaper = NoTrafficShaper(self.platform)

    self._patch_wpr_finder = mock.patch(
        "crossbench.network.replay.wpr.WprGoFinder.wpr",
        return_value=self.wpr_go_bin)
    self._patch_wpr_finder.start()
    self.addCleanup(self._patch_wpr_finder.stop)

  def _create_network(self, **kwargs: Any) -> LocalWprReplayNetwork:
    default_kwargs: dict[str, Any] = {
        "archive": self.archive_path,
        "traffic_shaper": self.traffic_shaper,
        "browser_platform": self.platform,
        "persist_server": False,
        "inject_deterministic_script": False,
        "no_archive_certificates": False,
        "response_transformations_file": None,
        "cross_platform_mode": False,
        "host": None,
        "expected_md5_hash": b"",
    }
    default_kwargs.update(kwargs)
    return LocalWprReplayNetwork(**default_kwargs)

  def test_validate_chromium_browser(self):
    network = self._create_network()

    browser = mock.Mock()
    browser.attributes().is_chromium_based = True
    # Validation should succeed for chromium browsers
    network.validate(browser)

    # Validation should fail for non-chromium browsers
    browser.attributes().is_chromium_based = False
    with self.assertRaises(ValueError) as cm:
      network.validate(browser)
    self.assertIn("only supports wpr replay in cross-platform mode",
                  str(cm.exception))

  @mock.patch("crossbench.network.replay.wpr.WprGoFinder.wpr")
  def test_validate_cross_platform_mode(self, mock_wpr_finder):
    mock_wpr_finder.return_value = self.wpr_go_bin
    network = self._create_network(cross_platform_mode=True)

    browser = mock.Mock()
    browser.attributes().is_chromium_based = True
    network.validate(browser)

    browser.attributes().is_chromium_based = False
    network.validate(browser)

  def test_validate_env_matching_hash(self):
    actual_hash = self._create_network()._archive_md5_hash
    self.assertTrue(actual_hash)
    self.assertIsInstance(actual_hash, bytes)
    self.assertEqual(len(actual_hash), 16)

    network_with_hash = self._create_network(expected_md5_hash=actual_hash)
    mock_env = mock.Mock()
    network_with_hash.validate_env(mock_env)
    mock_env.handle_warning.assert_not_called()

  def test_validate_env_mismatched_hash(self):
    mismatched_hash = b"\x00" * 16
    network = self._create_network(expected_md5_hash=mismatched_hash)

    mock_env = mock.Mock()
    network.validate_env(mock_env)
    mock_env.handle_warning.assert_called_once()
    warning_msg = mock_env.handle_warning.call_args[0][0]
    self.assertIn("WPR archive hash mismatch", warning_msg)
    self.assertIn(mismatched_hash.hex(), warning_msg)

  def test_invalid_md5_hash_raises(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      self._create_network(expected_md5_hash="not-a-valid-md5-hash")

  def test_set_archive_path_invalidates_cached_hash(self):
    network = self._create_network()
    first_hash = network._archive_md5_hash
    other_archive = pathlib.Path("/wpr/other_archive.wprgo")
    self.fs.create_file(other_archive, contents=b"different content")
    network.set_archive_path(other_archive)
    second_hash = network._archive_md5_hash
    self.assertNotEqual(first_hash, second_hash)

  def test_validate_env_empty_hash(self):
    network = self._create_network(expected_md5_hash=b"")
    mock_env = mock.Mock()
    network.validate_env(mock_env)
    mock_env.handle_warning.assert_not_called()

  def test_network_config_passes_expected_md5_hash(self):
    valid_hash_str = "a" * 32
    valid_hash_bytes = bytes.fromhex(valid_hash_str)
    config = NetworkConfig.parse({
        "type": "wpr",
        "path": str(self.archive_path),
        "expected_md5_hash": valid_hash_str
    })
    self.assertEqual(config.expected_md5_hash, valid_hash_bytes)
    network = config.create_network(self.platform)
    self.assertIsInstance(network, LocalWprReplayNetwork)
    self.assertEqual(network._expected_md5_hash, valid_hash_bytes)

  def test_network_config_rejects_expected_md5_hash_for_non_wpr(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      NetworkConfig(
          type=NetworkType.LIVE, expected_md5_hash=b"\xaa" * 16).validate()


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
