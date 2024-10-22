# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import contextlib

from crossbench import path as pth
from crossbench import plt


@contextlib.contextmanager
def tmp_platform_cache_dir(cache_dir: pth.LocalPath):
  old_cache_dir = plt.PLATFORM.cache_dir("test")
  plt.PLATFORM.set_cache_dir(cache_dir)
  try:
    yield
  finally:
    plt.PLATFORM.set_cache_dir(old_cache_dir)
