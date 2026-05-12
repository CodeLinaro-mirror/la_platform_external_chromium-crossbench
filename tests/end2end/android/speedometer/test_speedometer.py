# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

from typing import TYPE_CHECKING

from crossbench.cli.cli import CrossBenchCLI
from crossbench.parse import NumberParser
from tests import test_helper

if TYPE_CHECKING:
  from tests.test_helper import TestEnv


def _verify_metrics(test_env: TestEnv, version: str):
  with (test_env.results_dir / f"speedometer_{version}.csv").open() as csv:
    lines = csv.readlines()
    error_message = f"csv content: {lines}"
    assert "Score" in lines[-1], error_message
    assert NumberParser.positive_zero_float(
        lines[-1].split("\t")[-1]) > 0, error_message


def test_speedometer_2_1(browser_config, test_env: TestEnv) -> None:
  CrossBenchCLI().run([
      "sp2.1",
      f"--browser={browser_config}",
      f"--out-dir={test_env.results_dir}",
      "--iterations=1",
      "--stories=.*Vanilla.*",
      "--probe=performance.entries",
  ] + list(test_env.cq_flags) + [
      "--",
      "--disable-field-trial-config",
  ])
  _verify_metrics(test_env, "2.1")


def test_speedometer_3_0(browser_config, test_env: TestEnv) -> None:
  CrossBenchCLI().run([
      "sp3.0",
      f"--browser={browser_config}",
      f"--out-dir={test_env.results_dir}",
      "--iterations=2",
      "--stories=.*React.*",
      "--probe=perfetto:default",
      "--js-flags=--no-opt",
  ] + list(test_env.cq_flags))
  _verify_metrics(test_env, "3.0")


def test_speedometer_3_1(browser_config, test_env: TestEnv) -> None:
  CrossBenchCLI().run([
      "speedometer_3.1",
      f"--browser={browser_config}",
      f"--out-dir={test_env.results_dir}",
      "--iterations=1",
      "--stories=.*Vue.*",
  ] + list(test_env.cq_flags) + [
      "--",
      "--incognito",
  ])
  _verify_metrics(test_env, "3.1")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
