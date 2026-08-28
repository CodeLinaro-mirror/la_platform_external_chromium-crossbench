# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import Any


def GlobalSkipChecks(input_api: Any, file_path: str) -> bool:
  if input_api.fnmatch.fnmatch(file_path, "*protoc/gen/*"):
    return True
  if input_api.fnmatch.fnmatch(file_path, "*crossbench/third_party/*"):
    return True
  return False
