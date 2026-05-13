# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
from typing import TypeAlias

from crossbench.cli.parser import CBArgumentParser

Subparsers: TypeAlias = (
    argparse._SubParsersAction[CBArgumentParser]  # noqa: SLF001
)
