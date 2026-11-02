# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import zipfile

from crossbench import path as pth
from crossbench.browsers.downloader import ZipArchiveHelper
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase


class ZipArchiveHelperTestCase(BaseCrossbenchTestCase):

  def _create_zip(self, archive_name: str,
                  entries: dict[str, tuple[str, int]]) -> pth.LocalPath:
    archive_path = pth.LocalPath("download") / archive_name
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w") as zf:
      for name, (contents, unix_mode) in entries.items():
        zf.writestr(ZipArchiveHelper.create_zip_info(name, unix_mode), contents)
    return archive_path

  def test_extract(self) -> None:
    archive_path = self._create_zip(
        "archive.zip", {
            "app/bin": ("binary", ZipArchiveHelper.EXECUTABLE_MODE),
            "app/data.txt": ("data", ZipArchiveHelper.FILE_MODE),
        })
    dest_path = pth.LocalPath("extracted/app")
    result = ZipArchiveHelper.extract(self.platform, archive_path, dest_path)
    self.assertEqual(result, dest_path)
    self.assertEqual((dest_path / "app/data.txt").read_text(), "data")
    binary = dest_path / "app/bin"
    self.assertEqual(binary.read_text(), "binary")
    self.assertEqual(binary.stat().st_mode, ZipArchiveHelper.EXECUTABLE_MODE)

  def test_extract_subpath(self) -> None:
    archive_path = self._create_zip(
        "archive.zip", {
            "chrome-win64/chrome.exe":
                ("binary", ZipArchiveHelper.EXECUTABLE_MODE),
            "other/file.txt": ("other", ZipArchiveHelper.FILE_MODE),
        })
    dest_path = pth.LocalPath("extracted/app")
    ZipArchiveHelper.extract(self.platform, archive_path, dest_path,
                             pth.LocalPath("chrome-win64"))
    self.assertEqual((dest_path / "chrome.exe").read_text(), "binary")
    self.assertFalse((dest_path / "other").exists())

  def test_extract_missing_subpath(self) -> None:
    archive_path = self._create_zip(
        "archive.zip",
        {"other/file.txt": ("other", ZipArchiveHelper.FILE_MODE)})
    with self.assertRaisesRegex(ValueError, "Expected chrome-win64"):
      ZipArchiveHelper.extract(self.platform, archive_path,
                               pth.LocalPath("extracted/app"),
                               pth.LocalPath("chrome-win64"))

  def test_extract_invalid_subpath(self) -> None:
    archive_path = self._create_zip(
        "archive.zip", {"file.txt": ("data", ZipArchiveHelper.FILE_MODE)})
    invalid_subpaths = (
        pth.LocalPath("/abs/path"),
        pth.LocalPath(".."),
        pth.LocalPath("../outside"),
        pth.LocalPath("nested/../../outside"),
        pth.LocalPath("."),
        pth.LocalPath(""),
    )
    for subpath in invalid_subpaths:
      with (
          self.subTest(subpath=str(subpath)),
          self.assertRaisesRegex(ValueError, "Invalid archive subpath"),
      ):
        ZipArchiveHelper.extract(self.platform, archive_path,
                                 pth.LocalPath("extracted/app"), subpath)

  def test_extract_existing_dest(self) -> None:
    archive_path = self._create_zip(
        "archive.zip", {"file.txt": ("data", ZipArchiveHelper.FILE_MODE)})
    dest_path = pth.LocalPath("extracted/app")
    self.fs.create_dir(dest_path)
    with self.assertRaises(AssertionError):
      ZipArchiveHelper.extract(self.platform, archive_path, dest_path)

  def test_extract_symlink(self) -> None:
    archive_path = self._create_zip(
        "archive.zip", {
            "app/target.txt": ("data", ZipArchiveHelper.FILE_MODE),
            "app/link.txt": ("target.txt", ZipArchiveHelper.SYMLINK_MODE),
        })
    dest_path = pth.LocalPath("extracted/app")
    ZipArchiveHelper.extract(self.platform, archive_path, dest_path)
    link = dest_path / "app/link.txt"
    self.assertTrue(link.is_symlink())
    self.assertEqual(link.read_text(), "data")

  def test_extract_unsafe_entry_path(self) -> None:
    archive_path = self._create_zip(
        "unsafe.zip",
        {"../outside_symlink": ("target", ZipArchiveHelper.SYMLINK_MODE)})
    with self.assertRaisesRegex(ValueError, "Unsafe zip entry path"):
      ZipArchiveHelper.extract(self.platform, archive_path,
                               pth.LocalPath("extracted/app"))

  def test_extract_unsafe_symlink_target(self) -> None:
    archive_path = self._create_zip("unsafe_target.zip", {
        "inside_symlink":
            ("../../outside_target", ZipArchiveHelper.SYMLINK_MODE),
    })
    with self.assertRaisesRegex(ValueError, "Unsafe zip symlink target"):
      ZipArchiveHelper.extract(self.platform, archive_path,
                               pth.LocalPath("extracted/app"))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
