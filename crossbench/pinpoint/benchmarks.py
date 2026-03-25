# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import Final

from immutabledict import immutabledict

# Crossbench benchmarks without corresponding pinpoint benchmarks are None.
_PINPOINT_BENCHMARK_BY_CROSSBENCH_NAME: Final[immutabledict[
    str, str | None]] = immutabledict({
        "devtools_frontend": "devtools_frontend.crossbench",
        "embedder": "embedder.crossbench",
        "jetstream_1.1": "jetstream",
        "jetstream_2.0": "jetstream2.0.crossbench",
        "jetstream_2.1": "jetstream2.1.crossbench",
        "jetstream_2.2": "jetstream2.2.crossbench",
        "jetstream_3.0": "jetstream3.0.crossbench",
        "jetstream_main": "jetstream-main.crossbench",
        "loading": "loading.crossbench",
        "loadline-phone": "loadline_phone.crossbench",
        "loadline-phone-debug": None,
        "loadline-phone-fast": None,
        "loadline-tablet": "loadline_tablet.crossbench",
        "loadline-tablet-debug": None,
        "loadline-tablet-fast": None,
        "loadline2-phone": "loadline_phone2.crossbench",
        "loadline2-phone-debug": None,
        "loadline2-tablet": None,
        "loadline2-tablet-debug": None,
        "loadline2-webapi-phone": None,
        "loadline2-webapi-phone-debug": None,
        "manual": None,
        "memory": "memory.desktop",
        "motionmark_1.0": "motionmark1.0.crossbench",
        "motionmark_1.1": "motionmark1.1.crossbench",
        "motionmark_1.2": "motionmark1.2.crossbench",
        "motionmark_1.3": "motionmark1.3.crossbench",
        "motionmark_1.3.1": "motionmark1.3.1.crossbench",
        "motionmark_main": None,
        "powerline": None,
        "speedometer_1.0": "speedometer",
        "speedometer_2.0": "speedometer2.0.crossbench",
        "speedometer_2.1": "speedometer2.1.crossbench",
        "speedometer_3.0": "speedometer3.0.crossbench",
        "speedometer_3.1": "speedometer3.1.crossbench",
        "speedometer_main": "speedometer-main.crossbench",
        "webai": None,
    })

_CROSSBENCH_BENCHMARK_BY_PINPOINT_NAME: Final[immutabledict[
    str, str]] = immutabledict({
        v: k for k, v in _PINPOINT_BENCHMARK_BY_CROSSBENCH_NAME.items() if v
    })


def pinpoint_benchmark(crossbench_benchmark: str) -> str | None:
  return _PINPOINT_BENCHMARK_BY_CROSSBENCH_NAME.get(crossbench_benchmark)


def is_crossbench_benchmark(pinpoint_benchmark: str) -> bool:
  return pinpoint_benchmark in _CROSSBENCH_BENCHMARK_BY_PINPOINT_NAME
