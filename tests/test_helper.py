# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
from typing import Union
import pytest
import sys


def run_pytest(path: Union[str, pathlib.Path], *args):
  sys.exit(pytest.main([str(path), *args, *sys.argv[1:]]))
