# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import zipfile
from typing import TYPE_CHECKING, Iterable, override
from unittest import mock

from crossbench import path as pth
from crossbench.browsers.downloader import ZipArchiveHelper
from crossbench.plt.android_adb import Adb
from crossbench.plt.arch import MachineArch
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.mock_helper import (
  AndroidAdbMockPlatform,
  LinuxMockPlatform,
  MacOsMockPlatform,
  MockPlatformMixin,
  WinMockPlatform,
)

if TYPE_CHECKING:
  from crossbench.browsers.downloader import Downloader


class AbstractDownloaderTestCase(BaseCrossbenchTestCase, metaclass=abc.ABCMeta):
  __test__ = False
  OS_NAME: str = ""
  MACHINE: MachineArch = MachineArch.X64

  @override
  def setUp(self) -> None:
    super().setUp()
    self.cache_dir = pth.LocalPath("crossbench/binary_cache")
    self.platform.host_platform.set_cache_dir(self.cache_dir)
    self._fake_download_url = ""
    self._fake_zip_entry = ""

  @override
  # pyrefly: ignore[bad-override]
  def setup_platform(self) -> MockPlatformMixin:
    platform = self._create_os_platform()
    platform.use_mock_name = False
    platform.machine = self.MACHINE
    return platform

  def _create_os_platform(self) -> MockPlatformMixin:
    match self.OS_NAME:
      case "linux":
        return LinuxMockPlatform()
      case "macos":
        return MacOsMockPlatform()
      case "win":
        return WinMockPlatform()
      case "android":
        return AndroidAdbMockPlatform(
          host_platform=LinuxMockPlatform(), adb=self._create_mock_adb()
        )
    raise ValueError(f"Unsupported OS_NAME: {self.OS_NAME!r}")

  @property
  def mock_adb(self) -> mock.Mock:
    assert isinstance(self.platform, AndroidAdbMockPlatform)
    adb = self.platform.adb
    assert isinstance(adb, mock.Mock)
    return adb

  def _create_mock_adb(self) -> mock.Mock:
    adb = mock.Mock(spec=Adb)
    adb.packages.return_value = []
    return adb

  def _fake_adb_install_package(self, package_name: str) -> None:
    installed_packages: list[str] = self.mock_adb.packages.return_value

    def fake_install(*args, **kwargs) -> None:
      del args, kwargs
      if package_name not in installed_packages:
        installed_packages.append(package_name)

    self.mock_adb.install.side_effect = fake_install

  def _mock_json_response(self, data: object) -> mock.Mock:
    response = mock.Mock()
    response.json.return_value = data
    return response

  def _assert_valid_archive(
    self,
    archive_name: str,
    base_cls: type[Downloader],
    valid_cls: type[Downloader],
    invalid_classes: Iterable[type[Downloader]] = (),
  ) -> None:
    path = pth.LocalPath("download") / archive_name
    self.fs.create_file(path)
    self.assertTrue(base_cls.is_valid(path, self.platform))
    self.assertTrue(valid_cls.is_valid(path, self.platform))
    for invalid_cls in invalid_classes:
      self.assertFalse(invalid_cls.is_valid(path, self.platform))

  def _setup_fake_zip_download(
    self, expected_url: str, zip_entry: str, app_version: str
  ) -> None:
    self._fake_download_url = expected_url
    self._fake_zip_entry = zip_entry
    self.platform.search_app = self._search_existing_app
    self.platform.host_platform.download_to = mock.Mock(
      side_effect=self._fake_zip_download
    )
    self.platform.app_version = mock.Mock(return_value=app_version)

  def _search_existing_app(
    self, app_or_bin: pth.AnyPathLike
  ) -> pth.AnyPath | None:
    app_path = self.platform.path(app_or_bin)
    if self.platform.exists(app_path):
      return app_path
    return None

  def _fake_zip_download(self, url: str, dst: pth.LocalPath) -> None:
    self.assertEqual(url, self._fake_download_url)
    with zipfile.ZipFile(dst, "w") as zip_file:
      zip_file.writestr(
        ZipArchiveHelper.create_zip_info(
          self._fake_zip_entry, ZipArchiveHelper.EXECUTABLE_MODE
        ),
        "binary",
      )
