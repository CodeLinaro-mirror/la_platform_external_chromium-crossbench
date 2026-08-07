# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import contextlib
import functools
import tarfile
from typing import TYPE_CHECKING, Any, Callable, Iterator
from unittest import mock

from typing_extensions import override

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


class ResultsUploaderGitPatchTestCase(BaseCrossbenchTestCase):

  @override
  def setUp(self) -> None:
    super().setUp()
    self.out_dir.mkdir()
    self.run_dir = self.out_dir / "run_results"
    self.run_dir.mkdir()

  def _extract_patch(self, file_path: pth.LocalPath) -> bytes | None:
    """Extracts diff.patch from archive, or None if missing."""
    self.assertTrue(file_path.name.endswith(".tar.gz"))
    archive_id = file_path.name.removesuffix(".tar.gz")
    with tarfile.open(file_path, "r:gz") as tar:
      patch_name = f"{archive_id}/diff.patch"
      if patch_name not in tar.getnames():
        return None
      extracted = tar.extractfile(patch_name)
      assert extracted is not None
      return extracted.read()

  def _mock_upload(self, patches: list[bytes | None],
                   file_path: pth.LocalPath) -> str:
    """Mock upload side effect that captures patch bytes from the archive."""
    patches.append(self._extract_patch(file_path))
    return "gs://my-bucket/test/archive.tar.gz"

  @contextlib.contextmanager
  def _mock_git_and_uploader(
      self,
      crossbench_details: dict[str, Any],
      diff_content: str = "sample diff content",
  ) -> Iterator[Callable[[], bytes | None]]:
    """Context manager mocking git and uploader, yielding patch getter."""
    # Mutable list passed by reference to _mock_upload to capture the
    # extracted patch.
    patches: list[bytes | None] = []
    mock_uploader = mock.MagicMock(spec=BaseUploader)
    mock_uploader.upload.side_effect = functools.partial(
        self._mock_upload, patches)

    with (
        mock.patch(
            "crossbench.uploader.results_uploader._uploader_for_url",
            return_value=mock_uploader,
        ),
        mock.patch(
            "crossbench.plt.PLATFORM.crossbench_details",
            return_value=crossbench_details,
        ),
        mock.patch(
            "crossbench.plt.PLATFORM.sh_stdout", return_value=diff_content),
    ):
      yield lambda: patches[0] if patches else None

  def test_create_archive_parent_different_hash(self) -> None:
    """Verifies diff.patch is included when parent hash differs from current."""
    diff_content = "sample diff content"
    with self._mock_git_and_uploader(
        crossbench_details={
            "canonical_parent_hash": "11111111",
            "current_hash": "22222222",
            "has_uncommitted_changes": False,
        },
        diff_content=diff_content,
    ) as get_patch:
      results_uploader.upload(self.run_dir, "gs://my-bucket/test/")
      patch_bytes = get_patch()
      self.assertIsNotNone(patch_bytes)
      assert patch_bytes is not None
      self.assertEqual(patch_bytes.decode("utf-8"), diff_content)

  def test_create_archive_uncommitted_changes(self) -> None:
    """Verifies diff.patch is included with uncommitted changes."""
    diff_content = "sample diff content"
    with self._mock_git_and_uploader(
        crossbench_details={
            "canonical_parent_hash": "11111111",
            "current_hash": "11111111",
            "has_uncommitted_changes": True,
        },
        diff_content=diff_content,
    ) as get_patch:
      results_uploader.upload(self.run_dir, "gs://my-bucket/test/")
      patch_bytes = get_patch()
      self.assertIsNotNone(patch_bytes)
      assert patch_bytes is not None
      self.assertEqual(patch_bytes.decode("utf-8"), diff_content)

  def test_create_archive_no_changes(self) -> None:
    """Verifies diff.patch is omitted when there are no git changes."""
    with self._mock_git_and_uploader(
        crossbench_details={
            "canonical_parent_hash": "11111111",
            "current_hash": "11111111",
            "has_uncommitted_changes": False,
        },) as get_patch:
      results_uploader.upload(self.run_dir, "gs://my-bucket/test/")
      self.assertIsNone(get_patch())

  def test_create_archive_empty_diff(self) -> None:
    """Verifies diff.patch is omitted when git diff returns an empty string."""
    with self._mock_git_and_uploader(
        crossbench_details={
            "canonical_parent_hash": "11111111",
            "current_hash": "22222222",
            "has_uncommitted_changes": True,
        },
        diff_content="",
    ) as get_patch:
      results_uploader.upload(self.run_dir, "gs://my-bucket/test/")
      self.assertIsNone(get_patch())

  def test_create_archive_no_current_hash(self) -> None:
    """Verifies diff.patch is omitted when no current hash is available."""

    crossbench_details = {
        "canonical_parent_hash": "11111111",
        "has_uncommitted_changes": True,
    }

    with self._mock_git_and_uploader(
        crossbench_details=crossbench_details,) as get_patch:
      results_uploader.upload(self.run_dir, "gs://my-bucket/test/")
      self.assertIsNone(get_patch())

    # Repeat with an empty `current_hash` entry.
    crossbench_details["current_hash"] = ""
    with self._mock_git_and_uploader(
        crossbench_details=crossbench_details,) as get_patch:
      results_uploader.upload(self.run_dir, "gs://my-bucket/test/")
      self.assertIsNone(get_patch())

  def test_create_archive_no_parent_hash(self) -> None:
    """Verifies diff.patch is omitted when no parent hash is available."""

    crossbench_details = {
        "current_hash": "11111111",
        "has_uncommitted_changes": True,
    }

    with self._mock_git_and_uploader(
        crossbench_details=crossbench_details,) as get_patch:
      results_uploader.upload(self.run_dir, "gs://my-bucket/test/")
      self.assertIsNone(get_patch())

    # Repeat with an empty `canonical_parent_hash` entry.
    crossbench_details["canonical_parent_hash"] = ""
    with self._mock_git_and_uploader(
        crossbench_details=crossbench_details,) as get_patch:
      results_uploader.upload(self.run_dir, "gs://my-bucket/test/")
      self.assertIsNone(get_patch())


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
