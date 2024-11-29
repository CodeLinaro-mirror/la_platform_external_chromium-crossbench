# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json

from crossbench.cli.cli import CrossBenchCLI
from tests import test_helper


def _logcat_config() -> str:
  return json.dumps({"filterspec": "ActivityManager:V *:S"})


def test_logcat(browser_config, output_dir) -> None:
  cli = CrossBenchCLI()
  result_dir = output_dir / "result"
  cli.run([
      "loading", "--url=blank", f"--browser={browser_config}",
      f"--probe=logcat:{_logcat_config()}", "--throw", f"--out-dir={result_dir}"
  ])

  logcat_files = list(result_dir.glob("*/runs/0/logcat.txt"))
  assert len(logcat_files) == 1
  with logcat_files[0].open() as logcat_file:
    lines = logcat_file.readlines()
    assert len(lines) > 1
    assert "--------- beginning of system" in lines[0]
    for line in lines[1:]:
      assert "ActivityManager" in line


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
