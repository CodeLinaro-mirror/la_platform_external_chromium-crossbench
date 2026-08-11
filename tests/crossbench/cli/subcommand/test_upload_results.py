# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from unittest import mock

from crossbench.cli.cli import CrossBenchCLI
from crossbench.cli.subcommand.upload_results import UploadResultsSubcommand
from tests import test_helper
from tests.crossbench.base import BaseCliTestCase, SysExitTestException


class UploadResultsSubcommandTest(BaseCliTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.cli_instance = CrossBenchCLI()
    self.subcommand = self.cli_instance.subcommands["upload-results"]
    self.assertIsInstance(self.subcommand, UploadResultsSubcommand)

  def test_run_success(self) -> None:
    test_dir = self.out_dir / "results"
    test_dir.mkdir(parents=True, exist_ok=True)
    target_url = "gs://test-bucket/results"

    with mock.patch(
        "crossbench.uploader.results_uploader.upload",
        return_value="https://storage.googleapis.com/test-bucket/results.tar.gz"
    ) as mock_upload:
      self.run_cli("upload-results", str(test_dir), target_url)
      mock_upload.assert_called_once_with(source=test_dir, target=target_url)

  def test_run_alias_success(self) -> None:
    test_dir = self.out_dir / "results"
    test_dir.mkdir(parents=True, exist_ok=True)
    target_url = "gs://test-bucket/results"

    with mock.patch(
        "crossbench.uploader.results_uploader.upload",
        return_value="https://storage.googleapis.com/test-bucket/results.tar.gz"
    ) as mock_upload:
      self.run_cli("upload_results", str(test_dir), target_url)
      mock_upload.assert_called_once_with(source=test_dir, target=target_url)

  def test_run_failure(self) -> None:
    test_dir = self.out_dir / "results"
    test_dir.mkdir(parents=True, exist_ok=True)
    target_url = "gs://test-bucket/results"

    with mock.patch(
        "crossbench.uploader.results_uploader.upload",
        return_value=None) as mock_upload:
      with self.assertRaises(SysExitTestException) as cm:
        self.run_cli("upload-results", str(test_dir), target_url)
      self.assertEqual(cm.exception.exit_code, 0)
      mock_upload.assert_called_once_with(source=test_dir, target=target_url)

  def test_invalid_result_dir(self) -> None:
    non_existent_dir = self.out_dir / "does_not_exist"
    target_url = "gs://test-bucket/results"

    with self.assertRaises(SysExitTestException):
      self.run_cli("upload-results", str(non_existent_dir), target_url)

  def test_invalid_target_url(self) -> None:
    test_dir = self.out_dir / "results"
    test_dir.mkdir(parents=True, exist_ok=True)

    with self.assertRaises(SysExitTestException):
      self.run_cli("upload-results", str(test_dir), "invalid://scheme")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
