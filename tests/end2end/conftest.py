# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import logging
import pathlib
import sys
import tempfile
from typing import Optional

import pytest

from crossbench import plt
from crossbench.browsers import all as browsers
from crossbench.parse import PathParser
from crossbench.path import LocalPath
from tests import test_helper

# pytest.fixtures rely on params having the same name as the fixture function
# pylint: disable=redefined-outer-name


def pytest_addoption(parser):
  parser.addoption(
      "--test-browser-path",
      "--browserpath",
      default=None,
      type=PathParser.path)
  parser.addoption(
      "--test-driver-path", "--driverpath", default=None, type=PathParser.path)
  parser.addoption(
      "--test-gsutil-path", "--gustilpath", default=None, type=PathParser.path)
  parser.addoption("--adb-device-id", default=None, type=str)
  parser.addoption("--adb-path", default=None, type=str)
  parser.addoption("--ignore-tests", default=None, type=str)


def pytest_xdist_auto_num_workers(config):
  del config
  if "linux" in sys.platform:
    return 2
  return 4


@pytest.fixture(scope="session", autouse=True)
def driver_path(request) -> Optional[pathlib.Path]:
  maybe_driver_path: Optional[LocalPath] = request.config.getoption(
      "--test-driver-path")
  if maybe_driver_path:
    logging.info("driver path: %s", maybe_driver_path)
    assert maybe_driver_path.exists()
  return maybe_driver_path


@pytest.fixture(scope="session", autouse=True)
def browser_path(request) -> Optional[pathlib.Path]:
  maybe_browser_path: Optional[pathlib.Path] = request.config.getoption(
      "--test-browser-path")
  if maybe_browser_path:
    logging.info("browser path: %s", maybe_browser_path)
    assert maybe_browser_path.exists()
    return maybe_browser_path
  logging.info("Trying default browser path for local runs.")
  try:
    return pathlib.Path(browsers.Chrome.stable_path(plt.PLATFORM))
  except ValueError as e:
    logging.warning("Unable to find Chrome Stable on %s, error=%s",
                    plt.PLATFORM, e)
    return None


@pytest.fixture(scope="session", autouse=True)
def gsutil_path(request) -> pathlib.Path:
  maybe_gsutil_path: Optional[pathlib.Path] = request.config.getoption(
      "--test-gsutil-path")
  if maybe_gsutil_path:
    logging.info("gsutil path: %s", maybe_gsutil_path)
    assert maybe_gsutil_path.exists()
    return maybe_gsutil_path
  logging.info("Trying default gsutil path for local runs.")
  return default_gsutil_path()


def default_gsutil_path() -> pathlib.Path:
  if maybe_gsutil_path := plt.PLATFORM.which("gsutil"):
    maybe_gsutil_path = plt.PLATFORM.local_path(maybe_gsutil_path)
    assert maybe_gsutil_path, "could not find fallback gsutil"
    assert maybe_gsutil_path.exists()
    return maybe_gsutil_path
  pytest.skip(f"Could not find gsutil on {plt.PLATFORM}")
  return pathlib.Path()


@pytest.fixture
def output_dir():
  with tempfile.TemporaryDirectory() as tmpdirname:
    yield pathlib.Path(tmpdirname)


@pytest.fixture(scope="session")
def root_dir() -> pathlib.Path:
  return test_helper.root_dir()


@pytest.fixture
def cache_dir(output_dir) -> pathlib.Path:
  path = output_dir / "cache"
  assert not path.exists()
  path.mkdir()
  return path


@pytest.fixture
def archive_dir(output_dir) -> pathlib.Path:
  path = output_dir / "archive"
  assert not path.exists()
  return path


@pytest.fixture(scope="session", autouse=True)
def device_id(request) -> Optional[str]:
  maybe_device_id: Optional[str] = request.config.getoption(
      "--adb-device-id")
  if maybe_device_id:
    logging.info("adb device id: %s", maybe_device_id)
    return maybe_device_id
  logging.info("No Android device detected.")
  return None


@pytest.fixture(scope="session", autouse=True)
def adb_path(request) -> Optional[str]:
  maybe_adb_path: Optional[str] = request.config.getoption(
      "--adb-path")
  if maybe_adb_path:
    logging.info("adb path: %s", maybe_adb_path)
    return maybe_adb_path
  logging.info("No custom adb path.")
  return None
