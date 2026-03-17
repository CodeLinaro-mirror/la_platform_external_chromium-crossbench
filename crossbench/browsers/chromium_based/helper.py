# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from crossbench import path as pth
  from crossbench.plt.base import Platform


BUILD_CHROMEDRIVER_INSTRUCTIONS: str = (
    "Please build 'chromedriver' manually for local builds, or "
    "clang_x64/chromedriver if you're running on Android. E.g. autoninja -C "
    "out/Default chromedriver")


def find_build_dir(path: pth.AnyPath,
                   platform: Platform,
                   limit: int = 5) -> pth.AnyPath | None:
  for parent in path.parents[:limit]:
    if is_build_dir(parent, platform):
      return parent
  return None


def is_build_dir(path: pth.AnyPath, platform: Platform) -> bool:
  return platform.is_file(path / "args.gn")


def is_in_build_dir(path: pth.AnyPath, platform: Platform) -> bool:
  # bypass potentially expensive checks
  if "src" not in path.parts:
    return False
  return bool(find_build_dir(path, platform))
