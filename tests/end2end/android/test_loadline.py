# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
import logging
import pathlib
import tempfile
from typing import Iterator

import pytest

from crossbench import compat
from crossbench.browsers.chrome.version import ChromeVersion
from crossbench.cli.cli import CrossBenchCLI
from crossbench.network.replay.wpr import WPR_PREBUILT_LOOKUP
from crossbench.path import check_hash
from crossbench.plt import PLATFORM
from crossbench.plt.android_adb import Adb, AndroidAdbPlatform
from tests import test_helper

# pytest.fixtures rely on params having the same name as the fixture function
# pylint: disable=redefined-outer-name

CHROME_APK_URL = "gs://chrome-telemetry/apks/MonochromeCanary.apk"
CHROME_APK_HASH = "5de59881c02783d2174e1e891d82c9dbbce09c67"

MIN_VERSION = ChromeVersion.any((130,))

@pytest.fixture(scope="session")
def tmp_dir(device_id, adb_path) -> Iterator[pathlib.Path]:
  with tempfile.TemporaryDirectory() as tmp_dir_name:
    tmp_dir = pathlib.Path(tmp_dir_name)

    adb = Adb(PLATFORM, device_id, adb_path)
    adb_platform = AndroidAdbPlatform(PLATFORM, adb=adb)

    installed_version_str = adb_platform.app_version("com.android.chrome")
    installed_version = ChromeVersion.parse(installed_version_str)
    if installed_version >= MIN_VERSION:
      logging.info("Using pre-installed chrome version %s", installed_version)
    else:
      # Download and install chrome-canary M130 (x64 arch) from the cloud.
      # The benchmark requires trace events that were introduced in M126.
      # TODO(crbug/377290309): Remove this workaround when chrome preinstalled
      # in the emulator image is >=M126.
      local_apk = tmp_dir / "chrome.apk"
      PLATFORM.sh("gsutil", "cp", CHROME_APK_URL, local_apk, check=True)
      assert check_hash(local_apk, CHROME_APK_HASH)

      assert adb_path, "Missing adb"
      assert device_id, "Missing device id"
      adb = Adb(PLATFORM, device_id, adb_path)
      adb.install_apk(local_apk)

    # Download prebuilt wprgo binary to run WPR on the host
    # TODO(crbug/377290309): Make the test work with on-device WPR.
    local_wpr = tmp_dir / "wprgo"
    wpr_cloud_binary = WPR_PREBUILT_LOOKUP[PLATFORM.key]
    PLATFORM.sh("gsutil", "cp", wpr_cloud_binary.url, local_wpr)
    assert check_hash(local_wpr, wpr_cloud_binary.file_hash)
    PLATFORM.sh("chmod", "+x", local_wpr)

    yield tmp_dir


# TODO(crbug/377290309): Remove the custom browser config when the test passes
# with the preinstalled browser.
def _browser_config(device_id, adb_path) -> str:
  return json.dumps({
      "browser": "chrome-canary",
      "driver": {
          "type": "adb",
          "device_id": device_id,
          "adb_bin": adb_path
      }
  })


class BenchmarkType(compat.StrEnum):
  PHONE = "loadline-phone"
  TABLET = "loadline-tablet"


ARCHIVE_URL = {
    BenchmarkType.PHONE:
        "gs://chrome-partner-telemetry/loading_benchmark/archive_phone.wprgo",
    BenchmarkType.TABLET:
        "gs://chrome-partner-telemetry/loading_benchmark/archive_tablet.wprgo"
}

# TODO(crbug/377290309): Remove the custom network config when the test passes
# with on-device WPR.
def _network_config(tmp_dir, benchmark_type) -> str:
  return json.dumps({
      "type": "wpr",
      "url": ARCHIVE_URL[benchmark_type],
      "wpr_go_bin": str(tmp_dir / "wprgo"),
      "persist_server": False,
      "run_on_device": False
  })


def _verify_experimental_metrics(out_dir):
  expected_files = {
      "loadline_benchmark_score.csv",
      "loadline_experimental_interaction_latency.csv",
      "loadline_experimental_sequence_manager.csv",
      "loadline_experimental_v8_rcs.csv", "loadline_experimental_cpu.csv",
      "loadline_experimental_mojo.csv", "loadline_experimental_tlp.csv",
      "loadline_experimental_web_features.csv", "loadline_experimental_dom.csv",
      "loadline_experimental_resources.csv", "loadline_experimental_v8.csv",
      "loadline_experimental_worker.csv"
  }
  for run in range(5):
    tp_output_files = list(out_dir.glob(f"*/runs/{run}/trace_processor/*.csv"))
    assert set(f.name for f in tp_output_files) == expected_files

    # Some metrics for some runs might have no values. But we expect at
    # least one metric to have some values.
    has_metric_values = False
    for f in tp_output_files:
      with f.open() as output_file:
        lines = output_file.readlines()
        assert len(lines) >= 1
        if len(lines) >= 2:
          has_metric_values = True
        num_columns = len(lines[0].split(","))
        assert num_columns > 0

    assert has_metric_values


@pytest.mark.parametrize("benchmark_type,use_experimental_metrics",
                         [(BenchmarkType.PHONE, False),
                          (BenchmarkType.TABLET, False),
                          (BenchmarkType.PHONE, True)])
def test_loadline(device_id, adb_path, root_dir, tmp_dir, benchmark_type,
                  use_experimental_metrics) -> None:
  cli = CrossBenchCLI()
  browser_config = _browser_config(device_id, adb_path)
  network_config = _network_config(tmp_dir, benchmark_type)
  out_dir = tmp_dir / f"result_{benchmark_type}_{use_experimental_metrics}"
  cmd = [
      benchmark_type, f"--browser={browser_config}", "--repeat=1",
      f"--network={network_config}", "--throw", f"--out-dir={out_dir}"
  ]
  if use_experimental_metrics:
    probe_config = (
        root_dir / "config/benchmark/loadline/probe_config_experimental.hjson")
    cmd.append(f"--probe-config={probe_config}")
  cli.run(cmd)

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
      assert float(value) > 0, f"Expected positive number, but got {value}"

  if use_experimental_metrics:
    _verify_experimental_metrics(out_dir)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
