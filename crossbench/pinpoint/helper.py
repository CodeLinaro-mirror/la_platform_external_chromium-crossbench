# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import contextlib
from typing import Iterator

from crossbench import exception
from crossbench.cli import ui


@contextlib.contextmanager
def annotate(name: str) -> Iterator[None]:
  with exception.annotate(name), ui.spinner(title=name):
    yield
