# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import argparse
import base64
import pathlib
from typing import Any
from unittest import mock

from crossbench import path as pth
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
      self.archive_path, contents=b"dummy wpr archive content"
    )
    self.wpr_go_bin = pathlib.Path("/wpr/wpr.go")
    self.fs.create_file(self.wpr_go_bin, contents=b"dummy wpr binary")
    self.traffic_shaper = NoTrafficShaper(self.platform)

    self._patch_wpr_finder = mock.patch(
      "crossbench.network.replay.wpr.WprGoFinder.wpr",
      return_value=self.wpr_go_bin,
    )
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
    self.assertIn(
      "only supports wpr replay in cross-platform mode", str(cm.exception)
    )

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
    config = NetworkConfig.parse(
      {
        "type": "wpr",
        "path": str(self.archive_path),
        "expected_md5_hash": valid_hash_str,
      }
    )
    self.assertEqual(config.expected_md5_hash, valid_hash_bytes)
    network = config.create_network(self.platform)
    self.assertIsInstance(network, LocalWprReplayNetwork)
    self.assertEqual(network._expected_md5_hash, valid_hash_bytes)

  def test_network_config_rejects_expected_md5_hash_for_non_wpr(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      NetworkConfig(
        type=NetworkType.LIVE, expected_md5_hash=b"\xaa" * 16
      ).validate()

  @mock.patch("crossbench.plt.base.gcloud_storage.Client")
  def test_get_gcs_blob_generation(self, mock_client_cls):
    mock_bucket = mock_client_cls.return_value.bucket.return_value
    blob_url = (
      "gs://chrome-partner-loadline/power/cnn_20260513.wprgo#1778683962813986"
    )
    self.platform.get_gcs_blob(blob_url)
    mock_bucket.blob.assert_called_once_with(
      "power/cnn_20260513.wprgo", generation=1778683962813986
    )

    mock_bucket.blob.reset_mock()
    self.platform.get_gcs_blob(
      "gs://chrome-partner-loadline/power/cnn_20260513.wprgo"
    )
    mock_bucket.blob.assert_called_once_with(
      "power/cnn_20260513.wprgo", generation=None
    )

    for invalid_fragment in ("0", "-1", "invalid"):
      with self.subTest(fragment=invalid_fragment):
        with self.assertRaises(argparse.ArgumentTypeError):
          self.platform.get_gcs_blob(
            "gs://chrome-partner-loadline/power/"
            f"cnn_20260513.wprgo#{invalid_fragment}"
          )

  def _cached_wpr_path(self, stem: str, md5_bytes: bytes) -> pth.LocalPath:
    md5_b64 = base64.b64encode(md5_bytes).decode("ascii")
    return (
      self.platform.local_cache_dir("wpr")
      / f"{stem}_{pth.safe_filename(md5_b64)}.wprgo"
    )

  def test_ensure_archive_uses_cached_file_from_expected_md5_hash(self):
    md5_bytes = bytes.fromhex("04d258d7a6c207b41c591fbb55c53397")
    cached_path = self._cached_wpr_path("cnn_20260513", md5_bytes)
    self.fs.create_file(cached_path, contents=b"cached wpr archive")
    network = self._create_network()
    gcs_patcher = mock.patch.object(
      self.platform, "prepare_gcs_request", side_effect=AssertionError
    )
    gcs_mock = gcs_patcher.start()
    self.addCleanup(gcs_patcher.stop)

    resolved = network.ensure_archive(
      (
        "gs://chrome-partner-loadline/power/cnn_20260513.wprgo#1778683962813986"
      ),
      expected_md5_hash=md5_bytes,
    )

    self.assertEqual(resolved, cached_path)
    gcs_mock.assert_not_called()

  def test_ensure_archive_cache_miss_downloads_from_gcs(self):
    md5_bytes = bytes.fromhex("04d258d7a6c207b41c591fbb55c53397")
    md5_b64 = base64.b64encode(md5_bytes).decode("ascii")
    expected_path = self._cached_wpr_path("cnn_20260513", md5_bytes)
    network = self._create_network()
    blob_mock = mock.Mock(md5_hash=md5_b64)
    url = "gs://chrome-partner-loadline/power/cnn_20260513.wprgo"
    with (
      mock.patch.object(
        self.platform, "prepare_gcs_request", return_value=blob_mock
      ) as gcs_mock,
      mock.patch.object(self.platform, "download_gcs_file") as download_mock,
    ):
      resolved = network.ensure_archive(url, expected_md5_hash=md5_bytes)

    self.assertEqual(resolved, expected_path)
    gcs_mock.assert_called_once_with(url)
    download_mock.assert_called_once_with(url, expected_path)

  def test_ensure_archive_does_not_reuse_initial_md5_for_other_archive(self):
    init_md5 = bytes.fromhex("04d258d7a6c207b41c591fbb55c53397")
    other_md5 = bytes.fromhex("11111111111111111111111111111111")
    self.fs.create_file(
      self._cached_wpr_path("other", init_md5), contents=b"wrong archive"
    )
    other_b64 = base64.b64encode(other_md5).decode("ascii")
    expected_path = self._cached_wpr_path("other", other_md5)
    network = self._create_network(expected_md5_hash=init_md5)
    url = "gs://chrome-partner-loadline/power/other.wprgo"
    with (
      mock.patch.object(
        self.platform,
        "prepare_gcs_request",
        return_value=mock.Mock(md5_hash=other_b64),
      ) as gcs_mock,
      mock.patch.object(self.platform, "download_gcs_file"),
    ):
      resolved = network.ensure_archive(url)

    self.assertEqual(resolved, expected_path)
    gcs_mock.assert_called_once_with(url)

  def test_ensure_archive_invalid_expected_md5_hash_raises(self):
    network = self._create_network()

    with self.assertRaisesRegex(argparse.ArgumentTypeError, "MD5"):
      network.ensure_archive(
        "gs://chrome-partner-loadline/power/cnn_20260513.wprgo",
        expected_md5_hash="invalid-hash",
      )


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
