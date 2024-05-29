# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import json
import logging
import re
from typing import (TYPE_CHECKING, Dict, Final, List, Optional, Tuple, Type,
                    Union, cast)

from crossbench import helper
from crossbench import path as pth
from crossbench import plt
from crossbench.browsers.chrome.version import ChromeVersion
from crossbench.browsers.downloader import (DMGArchiveHelper, Downloader,
                                            IncompatibleVersionError,
                                            RPMArchiveHelper)
from crossbench.browsers.version import BrowserVersion, BrowserVersionChannel

if TYPE_CHECKING:
  from crossbench.plt.android_adb import Adb


class ChromeDownloader(Downloader):
  STORAGE_URL: str = "gs://chrome-signed/desktop-5c0tCh/"
  VERSION_URL = (
      "https://versionhistory.googleapis.com/v1/"
      "chrome/platforms/{platform}/channels/{channel}/versions?filter={filter}")
  VERSION_URL_PLATFORM_LOOKUP: Dict[Tuple[str, str], str] = {
      ("win", "ia32"): "win",
      ("win", "x64"): "win64",
      ("linux", "x64"): "linux",
      ("macos", "x64"): "mac",
      ("macos", "arm64"): "mac_arm64",
      ("android", "arm64"): "android",
  }

  @classmethod
  def is_valid_version(cls, path_or_identifier: str):
    return ChromeVersion.is_valid_unique(path_or_identifier)

  @classmethod
  def _is_valid(cls, path_or_identifier: pth.RemotePathLike,
                browser_platform: plt.Platform) -> bool:
    if cls.is_valid_version(str(path_or_identifier)):
      return True
    path = browser_platform.path(path_or_identifier)
    return (browser_platform.exists(path) and
            path.name.endswith(cls.ARCHIVE_SUFFIX))

  @classmethod
  def _get_loader_cls(cls,
                      browser_platform: plt.Platform) -> Type[ChromeDownloader]:
    if browser_platform.is_macos:
      return ChromeDownloaderMacOS
    if browser_platform.is_linux:
      return ChromeDownloaderLinux
    if browser_platform.is_win:
      return ChromeDownloaderWin
    if browser_platform.is_android:
      return ChromeDownloaderAndroid
    raise ValueError(
        "Downloading chrome is only supported on linux and macOS, "
        f"but not on {browser_platform.name} {browser_platform.machine}")

  def _pre_check(self) -> None:
    super()._pre_check()
    if self._requested_version and not self.host_platform.which("gsutil"):
      raise ValueError(
          f"Cannot download chrome version {self._requested_version}: "
          "please install gsutil.\n"
          "- https://cloud.google.com/storage/docs/gsutil_install\n"
          "- Run 'gcloud auth login' to get access to the archives "
          "(googlers only).")

  def _version_check(self) -> None:
    major_version: int = self._requested_version.major
    if (self._browser_platform.is_macos and self._browser_platform.is_arm64 and
        (major_version < 87)):
      raise ValueError(
          "Native Mac arm64/m1 Chrome version is available with M87, "
          f"but requested M{major_version}.")

  def _parse_version(self, version_identifier: str) -> BrowserVersion:
    return ChromeVersion.parse_unique(version_identifier)

  def _find_archive_url(self) -> Optional[str]:
    # Quick probe for complete versions
    if self._requested_version.is_complete:
      return self._find_exact_archive_url()
    return self._find_milestone_archive_url()

  def _find_milestone_archive_url(self) -> Optional[str]:
    milestone: int = self._requested_version.major
    platform = self.VERSION_URL_PLATFORM_LOOKUP.get(self._browser_platform.key)
    if not platform:
      raise ValueError(f"Unsupported platform {self._browser_platform}")
    # Version ordering is: stable < beta < dev < canary < canary_asan
    # See https://developer.chrome.com/docs/web-platform/versionhistory/reference#filter
    # TODO: respect channel
    url = self.VERSION_URL.format(
        platform=platform,
        channel="all",
        filter=f"version>={milestone},version<{milestone+1},channel<=canary&")
    logging.info("LIST ALL VERSIONS for M%s (slow): %s", milestone, url)
    try:
      with helper.urlopen(url) as response:
        raw_infos = json.loads(response.read().decode("utf-8"))["versions"]
        version_urls: List[str] = [
            f"{self.STORAGE_URL}{info['version']}/{self._platform_name}/"
            for info in raw_infos
        ]
    except Exception as e:
      raise ValueError(
          f"Could not find version {self._requested_version_str} "
          f"for {self._browser_platform.name} {self._browser_platform.machine} "
      ) from e
    logging.info("FILTERING %d CANDIDATES", len(version_urls))
    return self._filter_candidate_urls(version_urls)

  def _find_exact_archive_url(self) -> Optional[str]:
    assert self._requested_version.is_complete
    # TODO: respect channel
    test_url = (f"{self.STORAGE_URL}"
                f"{self._requested_version.parts_str}/{self._platform_name}/")
    logging.info("LIST VERSIONS for M%s: %s", self._requested_version, test_url)
    return self._filter_candidate_urls([test_url])

  def _filter_candidate_urls(self, versions_urls: List[str]) -> Optional[str]:
    version_items: List[Tuple[ChromeVersion, str]] = []
    for url in versions_urls:
      version_str, _ = url[len(self.STORAGE_URL):].split("/", maxsplit=1)
      version = tuple(map(int, version_str.split(".")))
      version_items.append((ChromeVersion(version,
                                          BrowserVersionChannel.ANY), url))
    version_items.sort(reverse=True)
    # Iterate from new to old version and and the first one that is older or
    # equal than the requested version.
    for version, url in version_items:
      if not self._requested_version.contains(version):
        logging.debug("Skipping download candidate: %s %s", version, url)
        continue
      for archive_url in self._archive_urls(url, version):
        try:
          result = self.host_platform.sh_stdout("gsutil", "ls", archive_url)
        except plt.SubprocessError as e:
          logging.debug("gsutil failed: %s", e)
          continue
        if result:
          return archive_url
    return None

  @abc.abstractmethod
  def _archive_urls(self, folder_url: str,
                    version: BrowserVersion) -> Tuple[str, ...]:
    pass

  def _download_archive(self, archive_url: str, tmp_dir: pth.LocalPath) -> None:
    self.host_platform.sh("gsutil", "cp", archive_url, tmp_dir)
    archive_candidates = list(tmp_dir.glob("*"))
    assert len(archive_candidates) == 1, (
        f"Download tmp dir contains more than one file: {tmp_dir}: "
        f"{archive_candidates}")
    candidate = archive_candidates[0]
    assert not self._archive_path.exists(), (
        f"Archive was already downloaded: {self._archive_path}")
    candidate.replace(self._archive_path)


class ChromeDownloaderLinux(ChromeDownloader):
  ARCHIVE_SUFFIX: str = ".rpm"

  @classmethod
  def is_valid(cls, path_or_identifier: pth.RemotePathLike,
               browser_platform: plt.Platform) -> bool:
    return cls._is_valid(path_or_identifier, browser_platform)

  def __init__(self,
               version_identifier: Union[str, pth.LocalPath],
               browser_type: str,
               platform_name: str,
               browser_platform: plt.Platform,
               cache_dir: Optional[pth.LocalPath] = None):
    assert not browser_type
    if browser_platform.is_linux and browser_platform.is_x64:
      platform_name = "linux64"
    else:
      raise ValueError("Unsupported linux architecture for downloading chrome: "
                       f"got={browser_platform.machine} supported=linux.x64")
    super().__init__(version_identifier, "chrome", platform_name,
                     browser_platform, cache_dir)

  def _extracted_path(self) -> pth.LocalPath:
    # TODO: support local vs remote
    return self._out_dir / self._requested_version_str

  def _installed_app_path(self) -> pth.LocalPath:
    return self._extracted_path() / "opt/google/chrome-unstable/chrome"

  def _archive_urls(self, folder_url: str,
                    version: BrowserVersion) -> Tuple[str, ...]:
    return (
        f"{folder_url}google-chrome-unstable-{version.parts_str}-1.x86_64.rpm",)

  def _install_archive(self, archive_path: pth.LocalPath) -> None:
    extracted_path = self._extracted_path()
    RPMArchiveHelper.extract(self.host_platform, archive_path, extracted_path)
    assert extracted_path.exists()


class ChromeDownloaderMacOS(ChromeDownloader):
  ARCHIVE_SUFFIX: str = ".dmg"
  MIN_MAC_ARM64_MILESTONE: Final[int] = 87

  @classmethod
  def is_valid(cls, path_or_identifier: pth.RemotePathLike,
               browser_platform: plt.Platform) -> bool:
    return cls._is_valid(path_or_identifier, browser_platform)

  def __init__(self,
               version_identifier: Union[str, pth.LocalPath],
               browser_type: str,
               platform_name: str,
               browser_platform: plt.Platform,
               cache_dir: Optional[pth.LocalPath] = None):
    assert not browser_type
    assert browser_platform.is_macos, f"{type(self)} can only be used on macOS"
    platform_name = "mac-universal"
    super().__init__(version_identifier, "chrome", platform_name,
                     browser_platform, cache_dir)

  def _download_archive(self, archive_url: str, tmp_dir: pth.LocalPath) -> None:
    assert self._browser_platform.is_macos
    if self._browser_platform.is_arm64 and (self._requested_version.major
                                            < self.MIN_MAC_ARM64_MILESTONE):
      raise ValueError(
          "Chrome Arm64 Apple Silicon is only available starting with M87, "
          f"but requested {self._requested_version_str} is too old.")
    super()._download_archive(archive_url, tmp_dir)

  def _archive_urls(self, folder_url: str,
                    version: BrowserVersion) -> Tuple[str, ...]:
    # TODO: respect channel
    version_str: str = version.parts_str
    stable_url = f"{folder_url}GoogleChrome-{version_str}.dmg"
    beta_url = f"{folder_url}GoogleChromeBeta-{version_str}.dmg"
    dev_url = f"{folder_url}GoogleChromeDev-{version_str}.dmg"
    canary_url = f"{folder_url}GoogleChromeCanary-{version_str}.dmg"
    return (stable_url, beta_url, dev_url, canary_url)

  def _extracted_path(self) -> pth.LocalPath:
    # TODO: support local vs remote
    return self._installed_app_path()

  def _installed_app_path(self) -> pth.LocalPath:
    return self._out_dir / f"Google Chrome {self._requested_version_str}.app"

  def _install_archive(self, archive_path: pth.LocalPath) -> None:
    extracted_path = self._extracted_path()
    if archive_path.suffix == ".dmg":
      DMGArchiveHelper.extract(self.host_platform, archive_path, extracted_path)
    else:
      raise ValueError(f"Unknown archive type: {archive_path}")
    assert extracted_path.exists()


class ChromeDownloaderAndroid(ChromeDownloader):
  ARCHIVE_SUFFIX: str = ".apk"
  STORAGE_URL: str = "gs://chrome-signed/android-B0urB0N/"

  @classmethod
  def is_valid(cls, path_or_identifier: pth.RemotePathLike,
               browser_platform: plt.Platform) -> bool:
    return cls._is_valid(path_or_identifier, browser_platform)

  def __init__(self,
               version_identifier: Union[str, pth.LocalPath],
               browser_type: str,
               platform_name: str,
               browser_platform: plt.Platform,
               cache_dir: Optional[pth.LocalPath] = None):
    assert not browser_type
    assert browser_platform.is_android, (
        f"{type(self)} can only be used on Android")
    # TODO: support more CPU types
    assert browser_platform.is_arm64, f"{type(self)} only supports arm64"
    platform_name = "arm_64"
    super().__init__(version_identifier, "chrome", platform_name,
                     browser_platform, cache_dir)

  @property
  def adb(self) -> Adb:
    return cast(plt.AndroidAdbPlatform, self._browser_platform).adb

  def _pre_check(self) -> None:
    super()._pre_check()
    assert self._browser_platform.is_android, (
        f"Expected android but got {self._browser_platform}")

  def _archive_urls(self, folder_url: str,
                    version: BrowserVersion) -> Tuple[str, ...]:
    prefix: str = f"{folder_url}"
    urls = []
    # TODO: respect version channel
    for channel in self.CHANNEL_PACKAGE_LOOKUP:
      urls.append(f"{prefix}Monochrome{channel}{self.ARCHIVE_SUFFIX}")
    return tuple(urls)

  def _extracted_path(self) -> pth.LocalPath:
    return self._archive_path

  def _installed_app_path(self) -> pth.LocalPath:
    for channel, package_name in self.CHANNEL_PACKAGE_LOOKUP.items():
      if channel in self._archive_url:
        logging.debug("Using package: %s", package_name)
        return pth.LocalPath(package_name)
    return pth.LocalPath(self.CHANNEL_PACKAGE_LOOKUP["Stable"])

  # TODO: add explicit channel selection support
  CHANNEL_PACKAGE_LOOKUP = {
      "Beta": "com.chrome.beta",
      "Dev": "com.chrome.dev",
      "Canary": "com.chrome.canary",
      # Let's check stable last to avoid overriding the default installation
      # if possible.
      "Stable": "com.android.chrome",
  }

  def _find_matching_installed_version(self) -> Optional[pth.LocalPath]:
    # TODO: we should use aapt and read the package name directly from
    # the apk: `aapt dump badging <path-to-apk> | grep package:\ name`
    # TODO: Add explicit channel selection
    # Iterate over all chrome versions and find any matching release
    installed_packages = self.adb.packages()
    for package_name in self.CHANNEL_PACKAGE_LOOKUP.values():
      if package_name not in installed_packages:
        continue
      try:
        package = pth.LocalPath(package_name)
        self._validate_installed(package)
        return package
      except IncompatibleVersionError as e:
        logging.debug("Ignoring installed package %s: %s", package_name, e)
    return None

  def _install_archive(self, archive_path: pth.LocalPath) -> None:
    # TODO: move browser installation to browser startup to allow
    # multiple versions on android in a single crossbench invocation
    package = str(self._installed_app_path())
    self.adb.uninstall(package, missing_ok=True)
    self.adb.install(archive_path, allow_downgrade=True)


class ChromeDownloaderWin(ChromeDownloader):
  # TODO: fully implement

  @classmethod
  def is_valid(cls, path_or_identifier: pth.RemotePathLike,
               browser_platform: plt.Platform) -> bool:
    return False

  def _archive_urls(self, folder_url: str,
                    version: BrowserVersion) -> Tuple[str, ...]:
    raise NotImplementedError("Downloading on Windows not yet supported")
