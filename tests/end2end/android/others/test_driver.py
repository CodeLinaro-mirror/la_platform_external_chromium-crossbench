# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json

import hjson

from crossbench.cli.cli import CrossBenchCLI
from crossbench.cli.config.driver import DriverConfig
from tests import test_helper


def test_specific_device_id(device_id, adb_path) -> None:
  config_dict = {"type": "adb", "device_id": device_id, "adb_bin": adb_path}
  driver_config = DriverConfig.parse(hjson.dumps(config_dict))
  assert driver_config.device_id == device_id


def test_cdp_driver(device_id, adb_path, test_env) -> None:
  browser_config = hjson.dumps({
      "browser": "chrome-stable",
      "driver": {
          "type": "cdp",
          "device_id": device_id,
          "adb_bin": adb_path
      }
  })
  args = [
      "loading",
      f"--browser={browser_config}",
      "--urls=blank",
      f"--out-dir={test_env.results_dir}",
      *list(test_env.cq_flags),
  ]

  cli = CrossBenchCLI()
  cli.run(args)

  result_files = list(test_env.results_dir.glob("cb.results.json"))
  assert len(result_files) == 1
  with result_files[0].open(encoding="utf-8") as f:
    result = json.load(f)
    assert result["success"]
    assert not result["errors"]


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
