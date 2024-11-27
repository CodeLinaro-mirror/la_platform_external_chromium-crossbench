# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json

from perfetto.trace_processor.api import TraceProcessor
import pytest

from crossbench.cli.cli import CrossBenchCLI
from tests import test_helper


def _profiling_config() -> str:
  return json.dumps({
      "target": "renderer_main_only",
      "pprof": False,
      "events": ["cpu-clock"],
      "count": 500000,
      "add_counters": ["context-switches"]
  })


@pytest.mark.xdist_group("end2end-mobile-benchmark")
def test_profiling_probe(browser_config, output_dir, adb_root) -> None:
  del adb_root
  cli = CrossBenchCLI()
  profiling_config = _profiling_config()
  result_dir = output_dir / "result"
  cli.run(["load", "--url=blank,2s", "--throw", f"--browser={browser_config}",
           f"--probe=profiling{profiling_config}", f"--out-dir={result_dir}"])

  simpleperf_files = list(result_dir.glob("*/runs/0/simpleperf.perf.data"))
  assert len(simpleperf_files) == 1
  assert simpleperf_files[0].is_file()

  with TraceProcessor(trace=str(simpleperf_files[0])) as tp:
    perf_sample_count = tp.query(
        "SELECT count(*) AS cnt FROM perf_sample").as_pandas_dataframe()
    assert perf_sample_count["cnt"][0] > 0
    perf_counters = list(tp.query(
        "SELECT name FROM perf_counter_track").as_pandas_dataframe()["name"])
    assert "cpu-clock" in perf_counters
    assert "context-switches" in perf_counters


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
