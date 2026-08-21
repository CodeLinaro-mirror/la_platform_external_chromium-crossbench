# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from unittest import mock

from crossbench.cli.cli import CrossBenchCLI
from crossbench.cli.subcommand.upload_results import UploadResultsSubcommand
from crossbench.probes.internal.summary import ResultsSummaryProbe
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
    (self.test_dir / ResultsSummaryProbe.FILE_NAME).touch()
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

  def test_run_symlink_success(self) -> None:
    """Verifies that single-hop symlinks to result directories are followed."""
    symlink = self.out_dir / "latest"
    symlink.symlink_to(self.test_dir)
    with mock.patch(
        _UPLOAD_PATCH_TARGET, return_value=_UPLOAD_RETURN_VALUE) as mock_upload:
      self.run_cli("upload-results", str(symlink), self.target_url)
      mock_upload.assert_called_once_with(
          source=self.test_dir, target=self.target_url)

  def test_run_chained_symlink_success(self) -> None:
    """Verifies that chained symlinks to result directories are followed."""
    symlink_1 = self.out_dir / "link1"
    symlink_1.symlink_to(self.test_dir)
    symlink_2 = self.out_dir / "link2"
    symlink_2.symlink_to(symlink_1)
    with mock.patch(
        _UPLOAD_PATCH_TARGET, return_value=_UPLOAD_RETURN_VALUE) as mock_upload:
      self.run_cli("upload-results", str(symlink_2), self.target_url)
      mock_upload.assert_called_once_with(
          source=self.test_dir, target=self.target_url)

  def test_run_file_fails(self) -> None:
    """Verifies that passing a file instead of a directory fails validation."""
    file_path = self.out_dir / "file.txt"
    file_path.touch()
    with self.assertRaises(SysExitTestException):
      self.run_cli("upload-results", str(file_path), self.target_url)

  def test_run_symlink_to_file_fails(self) -> None:
    """Verifies that symlinks pointing to files fail validation."""
    file_path = self.out_dir / "file.txt"
    file_path.touch()
    symlink = self.out_dir / "link_to_file"
    symlink.symlink_to(file_path)
    with self.assertRaises(SysExitTestException):
      self.run_cli("upload-results", str(symlink), self.target_url)

  def test_run_broken_symlink_fails(self) -> None:
    """Verifies that broken symlinks pointing nowhere fail validation."""
    symlink = self.out_dir / "broken"
    symlink.symlink_to(self.out_dir / "does_not_exist")
    with self.assertRaises(SysExitTestException):
      self.run_cli("upload-results", str(symlink), self.target_url)

  def test_run_symlink_loop_fails(self) -> None:
    """Verifies that cyclical symlink loops fail validation cleanly."""
    symlink_a = self.out_dir / "loop_a"
    symlink_b = self.out_dir / "loop_b"
    symlink_a.symlink_to(symlink_b)
    symlink_b.symlink_to(symlink_a)
    with self.assertRaises(SysExitTestException):
      self.run_cli("upload-results", str(symlink_a), self.target_url)

  def test_run_non_result_dir_fails(self) -> None:
    """Verifies that directories not recognized as result folders fail.

    To that end, a heuristic is employed - the presence or absence of a specific
    file.
    """
    non_result_dir = self.out_dir / "not_a_result_dir"
    non_result_dir.mkdir(parents=True, exist_ok=True)
    with self.assertRaises(SysExitTestException):
      self.run_cli("upload-results", str(non_result_dir), self.target_url)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
