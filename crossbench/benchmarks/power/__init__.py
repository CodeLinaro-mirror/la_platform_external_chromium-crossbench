# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from crossbench.benchmarks.power.idle import PowerIdleBenchmark
from crossbench.benchmarks.power.media_playback import \
    PowerMediaPlaybackBenchmark

__all__: list[str] = [
    "PowerIdleBenchmark",
    "PowerMediaPlaybackBenchmark",
]
