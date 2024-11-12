# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING, Final, Iterable, List, Tuple, TypeVar

from crossbench import plt

if TYPE_CHECKING:
  from crossbench.path import AnyPath
  PathT = TypeVar("PathT", bound=AnyPath)


def sort_by_file_size(files: Iterable[PathT],
                      platform: plt.Platform = plt.PLATFORM) -> List[PathT]:
  return sorted(files, key=lambda f: (platform.file_size(f), f.name))


SIZE_UNITS: Final[Tuple[str, ...]] = ("B", "KiB", "MiB", "GiB", "TiB")


def get_file_size(file: AnyPath,
                  digits: int = 2,
                  platform: plt.Platform = plt.PLATFORM) -> str:
  size: float = float(platform.file_size(file))
  unit_index = 0
  divisor = 1024.0
  while (unit_index < len(SIZE_UNITS)) and size >= divisor:
    unit_index += 1
    size /= divisor
  return f"{size:.{digits}f} {SIZE_UNITS[unit_index]}"
