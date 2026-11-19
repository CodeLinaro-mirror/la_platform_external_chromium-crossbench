# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from typing import NotRequired, TypedDict


class VersionDetails(TypedDict):
  version: str
  current_hash: NotRequired[str]
  canonical_parent_hash: NotRequired[str]
  has_uncommitted_changes: NotRequired[bool]
