# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager
from pathlib import Path
import sys


@contextmanager
def android_protoc_in_sys_path():
  prev_path = sys.path
  sys.path = [str(Path(__file__).parent.resolve())] + prev_path
  try:
    yield None
  finally:
    sys.path = prev_path
