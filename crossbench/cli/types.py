# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse

from crossbench.cli.parser import CBArgumentParser

type Subparsers = (
  argparse._SubParsersAction[CBArgumentParser]  # noqa: SLF001
)
