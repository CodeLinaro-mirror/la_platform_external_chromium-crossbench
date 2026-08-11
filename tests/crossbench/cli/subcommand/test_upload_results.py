# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from unittest import mock

from crossbench.cli.cli import CrossBenchCLI
from crossbench.cli.subcommand.upload_results import UploadResultsSubcommand
from tests import test_helper
from tests.crossbench.base import BaseCliTestCase, SysExitTestException

_UPLOAD_PATCH_TARGET = "crossbench.uploader.results_uploader.upload"
_UPLOAD_RETURN_VALUE = "gs://test-bucket/results/archive.tar.gz"


class UploadResultsSubcommandTest(BaseCliTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.cli_instance = CrossBenchCLI()
    self.subcommand = self.cli_instance.subcommands["upload-results"]
    self.assertIsInstance(self.subcommand, UploadResultsSubcommand)
    self.test_dir = self.out_dir / "results"
    self.test_dir.mkdir(parents=True, exist_ok=True)
    self.target_url = "gs://test-bucket/results"

  def test_run_success(self) -> None:
    with mock.patch(
        _UPLOAD_PATCH_TARGET, return_value=_UPLOAD_RETURN_VALUE) as mock_upload:
      self.run_cli("upload-results", str(self.test_dir), self.target_url)
      mock_upload.assert_called_once_with(
          source=self.test_dir, target=self.target_url)

  def test_run_alias_success(self) -> None:
    with mock.patch(
        _UPLOAD_PATCH_TARGET, return_value=_UPLOAD_RETURN_VALUE) as mock_upload:
      self.run_cli("upload_results", str(self.test_dir), self.target_url)
      mock_upload.assert_called_once_with(
          source=self.test_dir, target=self.target_url)

  def test_run_failure(self) -> None:
    with (
        mock.patch(_UPLOAD_PATCH_TARGET, return_value=None) as mock_upload,
        self.assertRaises(SysExitTestException) as cm,
    ):
      self.run_cli("upload-results", str(self.test_dir), self.target_url)
    self.assertEqual(cm.exception.exit_code, 0)
    mock_upload.assert_called_once_with(
        source=self.test_dir, target=self.target_url)

  def test_invalid_result_dir(self) -> None:
    non_existent_dir = self.out_dir / "does_not_exist"
    with self.assertRaises(SysExitTestException):
      self.run_cli("upload-results", str(non_existent_dir), self.target_url)

  def test_invalid_target_url(self) -> None:
    with self.assertRaises(SysExitTestException):
      self.run_cli("upload-results", str(self.test_dir), "invalid://scheme")

  def test_unsupported_target_url(self) -> None:
    with self.assertRaises(SysExitTestException):
      self.run_cli("upload-results", str(self.test_dir),
                   "https://unsupported-bucket/path")

  def test_default_env_var_target(self) -> None:
    env_target = "gs://env-bucket/results"
    with (
        mock.patch.dict("os.environ",
                        {"CROSSBENCH_RESULT_UPLOAD_TARGET": env_target}),
        mock.patch(_UPLOAD_PATCH_TARGET, return_value=_UPLOAD_RETURN_VALUE) as
        mock_upload,
    ):
      self.run_cli("upload-results", str(self.test_dir))
      mock_upload.assert_called_once_with(
          source=self.test_dir, target=env_target)

  def test_missing_target_url_no_env_var(self) -> None:
    with (
        mock.patch.dict("os.environ", {}, clear=True),
        self.assertRaises(SysExitTestException),
    ):
      self.run_cli("upload-results", str(self.test_dir))

  def test_explicit_target_url_overrides_env_var(self) -> None:
    env_target = "gs://env-bucket/results"
    explicit_target = "gs://explicit-bucket/results"
    with (
        mock.patch.dict("os.environ",
                        {"CROSSBENCH_RESULT_UPLOAD_TARGET": env_target}),
        mock.patch(_UPLOAD_PATCH_TARGET, return_value=_UPLOAD_RETURN_VALUE) as
        mock_upload,
    ):
      self.run_cli("upload-results", str(self.test_dir), explicit_target)
      mock_upload.assert_called_once_with(
          source=self.test_dir, target=explicit_target)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
