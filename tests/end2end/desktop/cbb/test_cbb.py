# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING

import pytest

from crossbench import plt
from crossbench.benchmarks import all as benchmarks
from crossbench.browsers.chrome import webdriver as chrome_webdriver
from crossbench.browsers.chromium import webdriver as chromium_webdriver
from crossbench.browsers.settings import Settings
from crossbench.cbb import cbb_adapter
from tests import test_helper

if TYPE_CHECKING:
  from crossbench.benchmarks.base import PressBenchmark
  from tests.test_helper import TestEnv

def get_benchmark(benchmark_cls) -> PressBenchmark:
  """Returns a benchmark instance for the corresponding benchmark_name"""
  story_class = cbb_adapter.get_pressbenchmark_story_cls(benchmark_cls.NAME)
  assert story_class
  stories = story_class.default_story_names()[:1]
  workload = story_class(substories=stories)
  benchmark_cls_lookup = cbb_adapter.get_pressbenchmark_cls(benchmark_cls.NAME)
  assert benchmark_cls_lookup, (
      f"Could not find benchmark class for '{benchmark_cls.NAME}'")
  assert benchmark_cls_lookup == benchmark_cls
  benchmark = benchmark_cls_lookup(stories=[workload])
  return benchmark


@pytest.fixture
def webdriver(driver_path, browser_path):
  is_cq = driver_path is not None
  flags = ["--headless"] if plt.PLATFORM.is_linux and is_cq else []
  browser_cls = chrome_webdriver.ChromeWebDriver
  if "chromium" in str(driver_path).lower():
    browser_cls = chromium_webdriver.ChromiumWebDriver
  return browser_cls("Chrome", browser_path,
                     Settings(driver_path=driver_path, flags=flags))


def run_benchmark(test_env: TestEnv, webdriver, benchmark_cls) -> None:
  """Tests that we can execute the specified benchmark and obtain result data
  post execution.
  This test uses Chrome browser to run the benchmarks.
  """
  benchmark = get_benchmark(benchmark_cls)
  assert benchmark

  maybe_results_file = cbb_adapter.get_probe_result_file(
      benchmark_cls.NAME, webdriver, test_env.results_dir)
  assert maybe_results_file
  results_file = pathlib.Path(maybe_results_file)
  assert not results_file.exists()

  cbb_adapter.run_benchmark(
      output_folder=test_env.results_dir,
      browser_list=[webdriver],
      benchmark=benchmark)

  assert results_file.exists()
  with results_file.open(encoding="utf-8") as f:
    benchmark_data = json.load(f)
  assert benchmark_data


def test_speedometer_20(test_env: TestEnv, webdriver):
  run_benchmark(test_env, webdriver, benchmarks.Speedometer20Benchmark)


def test_speedometer_21(test_env: TestEnv, webdriver):
  run_benchmark(test_env, webdriver, benchmarks.Speedometer21Benchmark)


def test_speedometer_30(test_env: TestEnv, webdriver):
  run_benchmark(test_env, webdriver, benchmarks.Speedometer30Benchmark)


def test_speedometer_31(test_env: TestEnv, webdriver):
  run_benchmark(test_env, webdriver, benchmarks.Speedometer31Benchmark)


def test_motionmark_12(test_env: TestEnv, webdriver):
  run_benchmark(test_env, webdriver, benchmarks.MotionMark12Benchmark)


def test_motionmark_13(test_env: TestEnv, webdriver):
  run_benchmark(test_env, webdriver, benchmarks.MotionMark13Benchmark)


def test_motionmark_131(test_env: TestEnv, webdriver):
  run_benchmark(test_env, webdriver, benchmarks.MotionMark131Benchmark)


def test_jetstream_20(test_env: TestEnv, webdriver):
  run_benchmark(test_env, webdriver, benchmarks.JetStream20Benchmark)


def test_jetstream_21(test_env: TestEnv, webdriver):
  run_benchmark(test_env, webdriver, benchmarks.JetStream21Benchmark)


def test_jetstream_22(test_env: TestEnv, webdriver):
  run_benchmark(test_env, webdriver, benchmarks.JetStream22Benchmark)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
