# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Final, Iterator

from crossbench import path as pth

PROTOC_DIR: Final[pth.LocalPath] = pth.ROOT_DIR / "third_party" / "protoc"
GEN_DIR: Final[pth.LocalPath] = PROTOC_DIR / "gen"


@contextmanager
def protoc_in_sys_path() -> Iterator[None]:
  prev_path = sys.path
  sys.path = [str(GEN_DIR), *prev_path]
  try:
    yield
  finally:
    sys.path = prev_path
