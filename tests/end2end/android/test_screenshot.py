# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from crossbench.cli.cli import CrossBenchCLI
from tests import test_helper


def test_screenshot(browser_config, output_dir) -> None:
  cli = CrossBenchCLI()
  result_dir = output_dir / "result"
  cli.run([
      "loading", "--url=blank", f"--browser={browser_config}",
      "--probe=screenshot:{}", "--throw", f"--out-dir={result_dir}"
  ])

  screenshots = list(result_dir.glob("*/runs/0/screenshot/*.png"))
  assert set(f.name for f in screenshots) == {
      "start.png", "start_story.png", "stop.png", "stop_story.png"
  }
  for f in screenshots:
    assert f.stat().st_size > 0


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
