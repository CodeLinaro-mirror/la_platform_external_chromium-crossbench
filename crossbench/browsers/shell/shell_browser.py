# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench.browsers.browser import Browser
from crossbench.parse import PathParser

if TYPE_CHECKING:
  from crossbench import path as pth


class ShellBrowser(Browser):

  @property
  @override
  def allow_existing_process(self) -> bool:
    return True

  @override
  def _resolve_binary(self,
                      path: pth.AnyPath) -> tuple[pth.AnyPath, pth.AnyPath]:
    path = PathParser.non_empty_file_path(path, "shell binary")
    return path, path
