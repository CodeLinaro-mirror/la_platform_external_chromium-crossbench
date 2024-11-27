# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
import pathlib
import tempfile

import pytest

from crossbench.cli.cli import CrossBenchCLI
from tests import test_helper

# pytest.fixtures rely on params having the same name as the fixture function
# pylint: disable=redefined-outer-nam


def _browser_config(device_id, adb_path) -> str:
  return json.dumps({
      "browser": "chrome-stable",
      "driver": {
          "type": "adb",
          "device_id": device_id,
          "adb_bin": adb_path
      }
  })


def _logcat_config() -> str:
  return json.dumps({"filterspec": "ActivityManager:V *:S"})


@pytest.mark.xdist_group("end2end-mobile-benchmark")
def test_logcat(device_id, adb_path) -> None:
  cli = CrossBenchCLI()
  browser_config = _browser_config(device_id, adb_path)

  with tempfile.TemporaryDirectory() as tmp_dir_name:
    tmp_dir = pathlib.Path(tmp_dir_name)
    out_dir = tmp_dir / "result"
    cli.run([
        "loading", "--url=blank", f"--browser={browser_config}",
        f"--probe=logcat:{_logcat_config()}", "--throw", f"--out-dir={out_dir}"
    ])

    logcat_files = list(out_dir.glob("*/runs/0/logcat.txt"))
    assert len(logcat_files) == 1
    with logcat_files[0].open() as logcat_file:
      lines = logcat_file.readlines()
      assert len(lines) > 1
      assert "--------- beginning of system" in lines[0]
      for line in lines[1:]:
        assert "ActivityManager" in line


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
