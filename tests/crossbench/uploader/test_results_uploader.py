# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import tarfile
from typing import TYPE_CHECKING
from unittest import mock

from typing_extensions import override

from crossbench.probes.internal.summary import ResultsSummaryProbe
from crossbench.uploader import results_uploader
from crossbench.uploader.base import BaseUploader
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase

if TYPE_CHECKING:
  from crossbench import path as pth


class ResultsUploaderTestCase(BaseCrossbenchTestCase):

  @override
  def setUp(self) -> None:
    super().setUp()
    self.out_dir.mkdir()

  def test_target_url_valid_target(self) -> None:
    """Supported scheme, valid URL - allowed."""
    url = "gs://my-bucket/test/"
    self.assertEqual(results_uploader.target_url(url), url)

  def test_target_url_unsupported_scheme(self) -> None:
    """Unsupported scheme, valid URL - disallowed."""
    with self.assertRaises(argparse.ArgumentTypeError):
      results_uploader.target_url("https://storage.googleapis.com/my-bucket/")

  def test_target_url_invalid_url(self) -> None:
    """Supported scheme, invalid URL - disallowed."""
    with self.assertRaises(argparse.ArgumentTypeError):
      results_uploader.target_url("gs://")

  def test_target_url_empty_with_env_var(self) -> None:
    url = "gs://my-bucket/env-target/"
    with mock.patch.dict("os.environ",
                         {"CROSSBENCH_RESULT_UPLOAD_TARGET": url}):
      self.assertEqual(results_uploader.target_url(""), url)

  def test_target_url_explicit_overrides_env_var(self) -> None:
    env_url = "gs://my-bucket/env-target/"
    explicit_url = "gs://my-bucket/explicit-target/"
    with mock.patch.dict("os.environ",
                         {"CROSSBENCH_RESULT_UPLOAD_TARGET": env_url}):
      self.assertEqual(results_uploader.target_url(explicit_url), explicit_url)

  def test_target_url_empty_without_env_var(self) -> None:
    with mock.patch.dict("os.environ", {}, clear=True):
      with self.assertRaises(argparse.ArgumentTypeError):
        results_uploader.target_url("")

  def test_create_archive_unique_filenames(self) -> None:
    run_dir = self.out_dir / "run_results"
    run_dir.mkdir(exist_ok=True)
    tmp_dir = self.out_dir / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    archive_path_1 = results_uploader._create_archive(run_dir, tmp_dir)
    archive_path_2 = results_uploader._create_archive(run_dir, tmp_dir)

    self.assertNotEqual(archive_path_1, archive_path_2)
    self.assertNotEqual(archive_path_1.name, archive_path_2.name)

  def test_upload(self) -> None:
    """Verifies that upload() archives results and delegates to backend."""
    run_dir = self.out_dir / "run_results"
    run_dir.mkdir()
    target_file = run_dir / "output.txt"
    target_file.write_text("data", encoding="utf-8")

    mock_uploader = mock.MagicMock(spec=BaseUploader)
    mock_uploader.upload.return_value = "gs://my-bucket/test/archive.tar.gz"

    with mock.patch(
        "crossbench.uploader.results_uploader._uploader_for_url",
        return_value=mock_uploader):
      result_url = results_uploader.upload(run_dir, "gs://my-bucket/test/")
      self.assertEqual(result_url, "gs://my-bucket/test/archive.tar.gz")
      mock_uploader.upload.assert_called_once()
      (archive_path,), _ = mock_uploader.upload.call_args
      self.assertEqual(archive_path.suffix, ".gz")

  def test_upload_failure(self) -> None:
    run_dir = self.out_dir / "run_results"
    run_dir.mkdir()

    mock_uploader = mock.MagicMock(spec=BaseUploader)
    mock_uploader.upload.side_effect = RuntimeError("GCS network failure")

    with mock.patch(
        "crossbench.uploader.results_uploader._uploader_for_url",
        return_value=mock_uploader):
      result_url = results_uploader.upload(run_dir, "gs://my-bucket/test/")
      self.assertIsNone(result_url)

  def _get_archive_symlink_member(
      self, symlink_rel_path: str,
      target_path: pth.LocalPath) -> tarfile.TarInfo:
    run_dir = self.out_dir / "run_results"
    run_dir.mkdir(exist_ok=True)
    symlink_file = run_dir / symlink_rel_path
    symlink_file.parent.mkdir(parents=True, exist_ok=True)
    symlink_file.symlink_to(target_path)

    archive_path = results_uploader._create_archive(run_dir, self.out_dir)
    archive_id = archive_path.name.removesuffix(".tar.gz")

    with tarfile.open(archive_path, "r:gz") as tar:
      return tar.getmember(f"{archive_id}/{symlink_rel_path}")

  def test_create_archive_root_symlink(self) -> None:
    target_file = self.out_dir / "run_results" / "output.txt"
    target_file.parent.mkdir(exist_ok=True)
    target_file.write_text("data", encoding="utf-8")

    member = self._get_archive_symlink_member("abs_link.txt", target_file)
    self.assertTrue(member.issym())
    self.assertEqual(member.linkname, "output.txt")

  def test_create_archive_nested_symlink(self) -> None:
    target_file = self.out_dir / "run_results" / "output.txt"
    target_file.parent.mkdir(exist_ok=True)
    target_file.write_text("data", encoding="utf-8")

    member = self._get_archive_symlink_member("sub/nested_link.txt",
                                              target_file)
    self.assertTrue(member.issym())
    self.assertEqual(member.linkname, "../output.txt")

  def test_create_archive_external_symlink(self) -> None:
    ext_target = self.out_dir / "external.txt"
    ext_target.write_text("ext", encoding="utf-8")

    member = self._get_archive_symlink_member("ext_link.txt", ext_target)
    self.assertTrue(member.issym())
    self.assertEqual(member.linkname, str(ext_target))


class ResultDirTestCase(BaseCrossbenchTestCase):

  @override
  def setUp(self) -> None:
    super().setUp()
    self.out_dir.mkdir()
    self.result_dir = self.out_dir / "run_results"
    self.result_dir.mkdir()
    (self.result_dir / ResultsSummaryProbe.FILE_NAME).touch()

  def test_result_dir_valid(self) -> None:
    """Verifies that a valid result directory is accepted."""
    resolved_dir = results_uploader.result_dir(str(self.result_dir))
    self.assertEqual(resolved_dir, self.result_dir)

  def test_result_dir_symlink_valid(self) -> None:
    """Verifies that a single-hop symlink to a result directory is resolved."""
    symlink = self.out_dir / "latest"
    symlink.symlink_to(self.result_dir)
    resolved_dir = results_uploader.result_dir(str(symlink))
    self.assertEqual(resolved_dir, self.result_dir)

  def test_result_dir_chained_symlink_valid(self) -> None:
    """Verifies that chained symlinks to a result directory are resolved."""
    symlink_1 = self.out_dir / "link1"
    symlink_1.symlink_to(self.result_dir)
    symlink_2 = self.out_dir / "link2"
    symlink_2.symlink_to(symlink_1)
    resolved_dir = results_uploader.result_dir(str(symlink_2))
    self.assertEqual(resolved_dir, self.result_dir)

  def test_result_dir_file_raises(self) -> None:
    """Verifies that passing a file instead of a directory raises an error."""
    file_path = self.out_dir / "some_file.txt"
    file_path.touch()
    with self.assertRaises(argparse.ArgumentTypeError):
      results_uploader.result_dir(str(file_path))

  def test_result_dir_symlink_to_file_raises(self) -> None:
    """Verifies that a symlink pointing to a file raises an error."""
    file_path = self.out_dir / "some_file.txt"
    file_path.touch()
    symlink = self.out_dir / "link_to_file"
    symlink.symlink_to(file_path)
    with self.assertRaises(argparse.ArgumentTypeError):
      results_uploader.result_dir(str(symlink))

  def test_result_dir_non_result_dir_raises(self) -> None:
    """Verifies that non-result directories raise an error.

    To that end, a heuristic is employed - the presence or absence of a specific
    file.
    """
    non_result_dir = self.out_dir / "not_a_result_dir"
    non_result_dir.mkdir()
    with self.assertRaises(argparse.ArgumentTypeError):
      results_uploader.result_dir(str(non_result_dir))

  def test_result_dir_non_existent_raises(self) -> None:
    """Verifies that non-existent paths raise an error."""
    with self.assertRaises(argparse.ArgumentTypeError):
      results_uploader.result_dir(str(self.out_dir / "does_not_exist"))

  def test_result_dir_broken_symlink_raises(self) -> None:
    """Verifies that broken symlinks raise an error."""
    symlink = self.out_dir / "broken"
    symlink.symlink_to(self.out_dir / "does_not_exist")
    with self.assertRaises(argparse.ArgumentTypeError):
      results_uploader.result_dir(str(symlink))

  def test_result_dir_symlink_loop_raises(self) -> None:
    """Verifies that cyclical symlink loops raise an error."""
    symlink_a = self.out_dir / "loop_a"
    symlink_b = self.out_dir / "loop_b"
    symlink_a.symlink_to(symlink_b)
    symlink_b.symlink_to(symlink_a)
    with self.assertRaises(argparse.ArgumentTypeError):
      results_uploader.result_dir(str(symlink_a))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
