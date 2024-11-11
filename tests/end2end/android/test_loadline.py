# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile

import pytest

from crossbench.cli.cli import CrossBenchCLI
from crossbench.path import check_hash
from tests import test_helper

# pytest.fixtures rely on params having the same name as the fixture function
# pylint: disable=redefined-outer-name

CHROME_APK_URL = "gs://chrome-telemetry/apks/MonochromeCanary.apk"
CHROME_APK_HASH = "5de59881c02783d2174e1e891d82c9dbbce09c67"
WPR_URL = ("gs://chromium-telemetry/binary_dependencies/"
           "wpr_go_6caa467dc6bef92e1c34256f539f8ed8f26a2fe1")
WPR_HASH = "6caa467dc6bef92e1c34256f539f8ed8f26a2fe1"


@pytest.fixture(scope="session")
def tmp_dir(device_id, adb_path) -> str:
  with tempfile.TemporaryDirectory() as tmp_dir_name:
    tmp_dir = pathlib.Path(tmp_dir_name)

    # Download and install chrome-canary M130 (x64 arch) from the cloud.
    # The benchmark requires trace events that were introduced in M126.
    # TODO(crbug/377290309): Remove this workaround when chrome preinstalled
    # in the emulator image is >=M126.
    local_apk = tmp_dir / "chrome.apk"
    subprocess.run(["gsutil", "cp", CHROME_APK_URL, local_apk], check=True)
    assert check_hash(local_apk, CHROME_APK_HASH)
    subprocess.run([adb_path, "-s", device_id, "install", local_apk],
                   check=True)

    # Download prebuilt wprgo binary to run WPR on the host
    # TODO(crbug/377290309): Make the test work with on-device WPR.
    local_wpr = tmp_dir / "wprgo"
    subprocess.run(["gsutil", "cp", WPR_URL, local_wpr], check=True)
    assert check_hash(local_wpr, WPR_HASH)
    subprocess.run(["chmod", "+x", local_wpr], check=True)

    yield tmp_dir


# TODO(crbug/377290309): Remove the custom browser config when the test passes
# with the preinstalled browser.
def _browser_config(device_id, adb_path) -> str:
  return json.dumps({
      "browser": "chrome-canary",
      "driver": {
          "type": "adb",
          "device_id": device_id,
          "adb_bin": adb_path,
      }
  })


# TODO(crbug/377290309): Remove the custom network config when the test passes
# with on-device WPR.
def _network_config(tmp_dir) -> str:
  return json.dumps({
      "type": "wpr",
      "url":
          "gs://chrome-partner-telemetry/loading_benchmark/archive_phone.wprgo",
      "wpr_go_bin": str(tmp_dir / "wprgo"),
      "persist_server": True,
      "run_on_device": False,
  })


def test_loadline_phone(device_id, adb_path, tmp_dir) -> None:
  cli = CrossBenchCLI()
  browser_config = _browser_config(device_id, adb_path)
  network_config = _network_config(tmp_dir)
  out_dir = tmp_dir / "result"
  cli.run(["loadline-phone", f"--browser={browser_config}", "--repeat=1",
           f"--network={network_config}", "--env-validation=skip", "--throw",
           f"--out-dir={out_dir}"])

  result_csv = out_dir / "loadline_probe.csv"
  with result_csv.open() as csv:
    lines = csv.readlines()
    assert len(lines) == 2

    titles = lines[0].split(",")
    assert len(titles) == 7
    assert titles[0] == "browser"
    assert titles[1] == "TOTAL_SCORE"

    values = lines[1].split(",")
    assert len(values) == 7
    for value in values[1:]:
      assert float(value) > 0


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
