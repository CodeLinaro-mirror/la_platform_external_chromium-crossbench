# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import enum
import json

from crossbench.cli.cli import CrossBenchCLI
from tests import test_helper
from tests.test_helper import TestEnv

# pytest.fixtures rely on params having the same name as the fixture function
# pylint: disable=redefined-outer-name


def _browser_config(device_id, adb_path) -> str:
  return json.dumps({
      "browser": "chrome-stable",
      "driver": {
          "type": "adb",
          "device_id": device_id,
          "adb_bin": adb_path
      }
  })


class BenchmarkType(enum.StrEnum):
  PHONE = "loadline2-phone"
  TABLET = "loadline2-tablet"


def _verify_default_metrics(out_dir, only_total=False):
  result_csv = out_dir / "loadline2_probe.csv"
  with result_csv.open() as csv:
    lines = csv.readlines()
    assert len(lines) == 2

    titles = lines[0].split(",")
    assert len(titles) == 7
    assert titles[0] == "browser"
    assert titles[1] == "TOTAL_SCORE"

    values = lines[1].split(",")
    assert len(values) == 7
    values_to_check = values[1:2] if only_total else values[1:]
    for value in values_to_check:
      assert value, f"Encountered empty value. CSV contents: {lines}"
      assert float(value) > 0, f"Expected positive number, but got {value}"


def test_loadline2_phone(device_id, adb_path, test_env: TestEnv) -> None:
  _test_loadline2_default(device_id, adb_path, BenchmarkType.PHONE, test_env)


def test_loadline2_tablet(device_id, adb_path, test_env: TestEnv) -> None:
  _test_loadline2_default(device_id, adb_path, BenchmarkType.TABLET, test_env)


def _test_loadline2_default(device_id, adb_path, benchmark_type,
                            test_env: TestEnv) -> None:
  cli = CrossBenchCLI()
  browser_config = _browser_config(device_id, adb_path)
  out_dir = test_env.results_dir / f"default_{benchmark_type}"
  cli.run([
      benchmark_type, f"--browser={browser_config}", "--repeat=1", "--throw",
      f"--out-dir={out_dir}", "--debug"
  ] + list(test_env.cq_flags))

  # With only 1 repetition, there's a chance that one story won't produce a
  # metric. To avoid flaky failures, we only check the total score here.
  _verify_default_metrics(out_dir, only_total=True)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
