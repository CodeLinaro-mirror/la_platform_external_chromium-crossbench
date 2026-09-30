# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import re
from typing import Any


def GlobalSkipChecks(input_api: Any, file_path: str) -> bool:
  if input_api.fnmatch.fnmatch(file_path, "third_party/*"):
    return True
  if input_api.fnmatch.fnmatch(file_path, "*crossbench/third_party/*"):
    return True
  return False


def GetBypassReason(description: str, key: str) -> str | None:
  if not description:
    return None
  pattern = rf"^\s*{re.escape(key)}\s*=\s*(.+)$"
  for match in re.finditer(pattern, description, re.MULTILINE | re.IGNORECASE):
    reason = match.group(1).strip()
    if reason and reason.lower() not in ("todo", "tbd", "none", "fixme", "xxx"):
      return reason
  return None
