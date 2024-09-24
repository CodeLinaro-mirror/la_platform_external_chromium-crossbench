# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import logging
import pathlib
import shutil
from typing import Union

import pytest

from crossbench import compat, plt
from crossbench.browsers.chrome.downloader import ChromeDownloader
from crossbench.browsers.chrome.webdriver import ChromeWebDriver
from crossbench.browsers.chromium.webdriver import (ChromeDriverFinder,
                                                    DriverNotFoundError)
from crossbench.browsers.settings import Settings
from tests import test_helper


def check_gsutil_access(gsutil_path: pathlib.Path):
  if gsutil_path == pathlib.Path():
    pytest.skip("Could not find gsutil")
  try:
    plt.PLATFORM.sh_stdout(
        gsutil_path, "ls",
        "gs://chrome-signed/desktop-5c0tCh/111.0.5563.19/linux64")
  except plt.SubprocessError as e:
    logging.info("Could not access chrome bucket with gsutil: %s", e)
    if "does not have storage.objects.list access" in str(e):
      pytest.skip(
          "gsutil likely has no access to gs://chrome-signed/desktop-5c0tCh")
    raise e


def _load_and_check_version(output_dir: pathlib.Path, archive_dir: pathlib.Path,
                            gsutil_path: pathlib.Path,
                            version_or_archive: Union[str, pathlib.Path],
                            version_str: str) -> pathlib.Path:
  check_gsutil_access(gsutil_path)
  with plt.PLATFORM.override_binary("gsutil", gsutil_path):
    app_path: pathlib.Path = ChromeDownloader.load(version_or_archive,
                                                   plt.PLATFORM, output_dir)
    assert compat.is_relative_to(app_path, output_dir)
    assert archive_dir.exists()
    assert app_path.exists()
    if plt.PLATFORM.is_macos:
      assert set(output_dir.iterdir()) == {app_path, archive_dir}
    assert version_str in plt.PLATFORM.app_version(app_path)
    archives = list(archive_dir.iterdir())
    assert len(archives) == 1
    assert app_path.exists()
    chrome = ChromeWebDriver(
        "test-chrome", app_path, settings=Settings(platform=plt.PLATFORM))
    assert version_str in chrome.version
    _load_and_check_chromedriver(output_dir, chrome)
    return app_path


def _load_and_check_chromedriver(output_dir, chrome: ChromeWebDriver) -> None:
  driver_dir = output_dir / "chromedriver-binaries"
  driver_dir.mkdir()
  finder = ChromeDriverFinder(chrome, cache_dir=driver_dir)
  assert not list(driver_dir.iterdir())
  with pytest.raises(DriverNotFoundError):
    finder.find_local_build()
  driver_path: pathlib.Path = finder.download()
  assert list(driver_dir.iterdir()) == [driver_path]
  assert driver_path.is_file()
  # Downloading again should use the cache-version
  driver_path: pathlib.Path = finder.download()
  assert list(driver_dir.iterdir()) == [driver_path]
  assert driver_path.is_file()
  # Restore output dir state.
  driver_path.unlink()
  driver_dir.rmdir()


def _delete_extracted_app(output_dir: pathlib.Path, app_version: str) -> None:
  for extracted_app_path in list(output_dir.iterdir()):
    if app_version in str(extracted_app_path):
      shutil.rmtree(str(extracted_app_path))


@pytest.mark.skipif(
    plt.PLATFORM.is_linux, reason="No canary versions on linux.")
def test_download_pre_115_canary(output_dir, archive_dir, gsutil_path) -> None:
  assert not list(output_dir.iterdir())
  _load_and_check_version(output_dir, archive_dir, gsutil_path,
                          "chrome-114.0.5735.2 canary", "114.0.5735.2")


def test_download_major_version_milestone(output_dir, archive_dir,
                                          gsutil_path) -> None:
  assert not list(output_dir.iterdir())
  _load_and_check_version(
      output_dir,
      archive_dir,
      gsutil_path,
      "chrome-M111",
      "111",
  )

  # Re-downloading should reuse the extracted app.
  app_path = _load_and_check_version(
      output_dir,
      archive_dir,
      gsutil_path,
      "chrome-M111",
      "111",
  )

  _delete_extracted_app(output_dir, "M111")
  assert not app_path.exists()
  _load_and_check_version(
      output_dir,
      archive_dir,
      gsutil_path,
      "chrome-M111",
      "111",
  )


def test_download_major_version_chrome_for_testing(output_dir, archive_dir,
                                                   gsutil_path) -> None:
  # Post M114 we're relying on the new chrome-for-testing download
  assert not list(output_dir.iterdir())
  _load_and_check_version(
      output_dir,
      archive_dir,
      gsutil_path,
      "chrome-M115",
      "115",
  )

  # Re-downloading should reuse the extracted app.
  app_path = _load_and_check_version(
      output_dir,
      archive_dir,
      gsutil_path,
      "chrome-M115",
      "115",
  )

  _delete_extracted_app(output_dir, "M115")
  assert not app_path.exists()
  _load_and_check_version(
      output_dir,
      archive_dir,
      gsutil_path,
      "chrome-M115",
      "115",
  )


def test_download_specific_version_pre_115_stable(output_dir, archive_dir,
                                                  gsutil_path) -> None:
  assert not list(output_dir.iterdir())
  version_str = "111.0.5563.146"
  _load_and_check_version(output_dir, archive_dir, gsutil_path,
                          f"chrome-{version_str}", version_str)

  # Re-downloading should work as well and hit the extracted app.
  app_path = _load_and_check_version(output_dir, archive_dir, gsutil_path,
                                     f"chrome-{version_str}", version_str)

  _delete_extracted_app(output_dir, version_str)
  assert not app_path.exists()
  app_path = _load_and_check_version(output_dir, archive_dir, gsutil_path,
                                     f"chrome-{version_str}", version_str)

  _delete_extracted_app(output_dir, version_str)
  assert not app_path.exists()
  archives = list(archive_dir.iterdir())
  assert len(archives) == 1
  archive = archives[0]
  app_path = _load_and_check_version(output_dir, archive_dir, gsutil_path,
                                     archive, version_str)
  assert list(archive_dir.iterdir()) == [archive]


@pytest.mark.skipif(
    plt.PLATFORM.is_macos and plt.PLATFORM.is_arm64,
    reason="Old versions only supported on intel machines.")
def test_download_old_major_version(output_dir, archive_dir,
                                    gsutil_path) -> None:
  assert not list(output_dir.iterdir())
  _load_and_check_version(output_dir, archive_dir, gsutil_path, "chrome-M68",
                          "68")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
