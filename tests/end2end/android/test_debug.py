# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json

from crossbench.cli.cli import CrossBenchCLI
from tests import test_helper


def test_debug(browser_config, output_dir) -> None:
  cli = CrossBenchCLI()
  result_dir = output_dir / "result"
  cli.run([
      "loading", "--url=blank", f"--browser={browser_config}", "--debug",
      f"--out-dir={result_dir}"
  ])

  result_files = list(result_dir.glob("*/runs/0/cb.results.json"))
  assert len(result_files) == 1
  with result_files[0].open() as f:
    result = json.load(f)
    assert result["success"]
    assert not result["errors"]


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
