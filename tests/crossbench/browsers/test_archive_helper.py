# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import subprocess
import zipfile
from unittest import mock

from typing_extensions import override

from crossbench import path as pth
from crossbench.browsers.downloader import RPMArchiveHelper, ZipArchiveHelper
from crossbench.plt.base import SubprocessError
from crossbench.plt.bin import Binaries, Binary
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.mock_helper import LinuxMockPlatform, MockPlatform


class RPMArchiveHelperTestCase(BaseCrossbenchTestCase):

  @override
  def setup_platform(self) -> MockPlatform:
    return LinuxMockPlatform()

  def _install_tool(self, binary: Binary) -> pth.LocalPath:
    tool_path = pth.LocalPath("/usr/bin") / binary.name
    self.fs.create_file(tool_path)
    self.platform.set_binary_lookup_override(binary.name, tool_path)
    return tool_path

  def _create_rpm(self, name: str = "archive.rpm") -> pth.LocalPath:
    archive_path = pth.LocalPath("download") / name
    self.fs.create_file(archive_path, contents="fake-rpm")
    return archive_path

  def test_extract_with_rpm2archive(self) -> None:
    rpm2archive = self._install_tool(Binaries.RPM2ARCHIVE)
    tar = self._install_tool(Binaries.TAR)
    self._install_tool(Binaries.RPM2CPIO)
    self._install_tool(Binaries.CPIO)
    archive_path = self._create_rpm()
    tar_file = archive_path.with_suffix(".tar")
    dest_path = pth.LocalPath("extracted/chrome")
    calls: list[tuple[str, ...]] = []

    def fake_sh(*args, **kwargs) -> subprocess.CompletedProcess:
      str_args = tuple(map(str, args))
      calls.append(str_args)
      if str_args[0] == str(rpm2archive):
        self.assertIsNotNone(kwargs.get("stdin"))
        self.assertIsNotNone(kwargs.get("stdout"))
      elif str_args[0] == str(tar):
        self.assertTrue(tar_file.is_file())
        self.assertTrue(dest_path.is_dir())
        self.fs.create_file(
            dest_path / "opt/google/chrome/chrome", contents="binary")
      return subprocess.CompletedProcess(args, 0)

    with mock.patch.object(self.platform, "sh", side_effect=fake_sh):
      result = RPMArchiveHelper.extract(self.platform, archive_path, dest_path)

    self.assertEqual(result, dest_path)
    self.assertEqual((dest_path / "opt/google/chrome/chrome").read_text(),
                     "binary")
    self.assertFalse(tar_file.exists())
    self.assertEqual(calls, [
        (str(rpm2archive), "--nocompression", "-"),
        (
            str(tar),
            "--extract",
            "--directory",
            str(dest_path),
            "--file",
            str(tar_file),
        ),
    ])

  def test_extract_fallback_to_rpm2cpio(self) -> None:
    rpm2cpio = self._install_tool(Binaries.RPM2CPIO)
    cpio = self._install_tool(Binaries.CPIO)
    archive_path = self._create_rpm()
    cpio_file = archive_path.with_suffix(".cpio")
    dest_path = pth.LocalPath("extracted/chrome")
    calls: list[tuple[str, ...]] = []

    def fake_sh(*args, **kwargs) -> subprocess.CompletedProcess:
      str_args = tuple(map(str, args))
      calls.append(str_args)
      if str_args[0] == str(rpm2cpio):
        self.assertIsNotNone(kwargs.get("stdout"))
      elif str_args[0] == str(cpio):
        self.assertIsNotNone(kwargs.get("stdin"))
        self.assertTrue(cpio_file.is_file())
        self.fs.create_file(
            dest_path / "opt/google/chrome/chrome", contents="binary")
      return subprocess.CompletedProcess(args, 0)

    with mock.patch.object(self.platform, "sh", side_effect=fake_sh):
      result = RPMArchiveHelper.extract(self.platform, archive_path, dest_path)

    self.assertEqual(result, dest_path)
    self.assertFalse(cpio_file.exists())
    self.assertEqual(calls, [
        (str(rpm2cpio), str(archive_path)),
        (
            str(cpio),
            "--extract",
            "--directory",
            str(dest_path),
            "--make-directories",
        ),
    ])

  def test_extract_rpm2archive_cleans_up_on_error_and_retries(self) -> None:
    rpm2archive = self._install_tool(Binaries.RPM2ARCHIVE)
    tar = self._install_tool(Binaries.TAR)
    archive_path = self._create_rpm()
    tar_file = archive_path.with_suffix(".tar")
    dest_path = pth.LocalPath("extracted/chrome")

    self.platform.expect_sh(rpm2archive, "--nocompression", "-", returncode=1)
    with self.assertRaises(SubprocessError):
      RPMArchiveHelper.extract(self.platform, archive_path, dest_path)
    self.assertFalse(tar_file.exists())
    self.assertFalse(dest_path.exists())

    self.platform.expect_sh(rpm2archive, "--nocompression", "-")
    self.platform.expect_sh(
        tar,
        "--extract",
        "--directory",
        dest_path,
        "--file",
        tar_file,
        returncode=2)
    with self.assertRaises(SubprocessError):
      RPMArchiveHelper.extract(self.platform, archive_path, dest_path)
    self.assertFalse(tar_file.exists())
    self.assertFalse(dest_path.exists())

  def test_extract_rpm2archive_empty_archive_raises(self) -> None:
    rpm2archive = self._install_tool(Binaries.RPM2ARCHIVE)
    tar = self._install_tool(Binaries.TAR)
    archive_path = self._create_rpm()
    tar_file = archive_path.with_suffix(".tar")
    dest_path = pth.LocalPath("extracted/chrome")

    self.platform.expect_sh(rpm2archive, "--nocompression", "-")
    self.platform.expect_sh(tar, "--extract", "--directory", dest_path,
                            "--file", tar_file)
    with self.assertRaisesRegex(ValueError, "Could not extract archive"):
      RPMArchiveHelper.extract(self.platform, archive_path, dest_path)
    self.assertFalse(tar_file.exists())
    self.assertFalse(dest_path.exists())

  def test_extract_rpm2cpio_cleans_up_on_error(self) -> None:
    rpm2cpio = self._install_tool(Binaries.RPM2CPIO)
    self._install_tool(Binaries.CPIO)
    archive_path = self._create_rpm()
    cpio_file = archive_path.with_suffix(".cpio")
    dest_path = pth.LocalPath("extracted/chrome")

    self.platform.expect_sh(rpm2cpio, archive_path, returncode=1)
    with self.assertRaises(SubprocessError):
      RPMArchiveHelper.extract(self.platform, archive_path, dest_path)
    self.assertFalse(cpio_file.exists())
    self.assertFalse(dest_path.exists())

  def test_extract_missing_tools(self) -> None:
    archive_path = self._create_rpm()
    with self.assertRaisesRegex(AssertionError, "rpm2archive or rpm2cpio"):
      RPMArchiveHelper.extract(self.platform, archive_path,
                               pth.LocalPath("extracted/chrome"))

  def test_extract_existing_dest(self) -> None:
    self._install_tool(Binaries.RPM2ARCHIVE)
    self._install_tool(Binaries.TAR)
    archive_path = self._create_rpm()
    dest_path = pth.LocalPath("extracted/chrome")
    self.fs.create_file(dest_path / "existing.txt", contents="keep")
    with self.assertRaisesRegex(AssertionError, "already exists"):
      RPMArchiveHelper.extract(self.platform, archive_path, dest_path)
    self.assertTrue((dest_path / "existing.txt").is_file())


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
