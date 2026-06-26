# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from crossbench.benchmarks.web_power.consolidated import WebPowerBenchmark
from crossbench.benchmarks.web_power.idle import WebPowerIdleBenchmark
from crossbench.benchmarks.web_power.media_playback import \
    WebPowerMediaPlaybackBenchmark
from crossbench.benchmarks.web_power.page_load import WebPowerPageLoadBenchmark
from crossbench.benchmarks.web_power.scroll import WebPowerScrollBenchmark

__all__: list[str] = [
    "WebPowerBenchmark",
    "WebPowerIdleBenchmark",
    "WebPowerMediaPlaybackBenchmark",
    "WebPowerPageLoadBenchmark",
    "WebPowerScrollBenchmark",
]
