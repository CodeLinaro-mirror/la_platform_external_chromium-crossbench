# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Final, Iterator

from typing_extensions import override

from crossbench import path as pth

if TYPE_CHECKING:
  from crossbench.plt.base import Platform

# TODO: these helpers should eventually migrate to plt/bin.


class BasePathFinder(abc.ABC):
  """Abstract base for all path-resolving helpers.

  This pure base class maintains strict decoupling from the global platform
  state, enabling safe usage during subsystem initialization.
  """

  @classmethod
  def find_binary(cls,
                  platform: Platform,
                  override: pth.AnyPath | None = None) -> pth.AnyPath | None:
    if override:
      return platform.parse_binary_path(override)
    return cls(platform).path

  def __init__(self, platform: Platform) -> None:
    self._platform: Final[Platform] = platform
    self._path: Final[pth.AnyPath | None] = self._find_path()
    if self._path and not self.is_valid_path(self._path):
      raise ValueError(f"Resolved binary path is not valid: {self._path}")

  @property
  def platform(self) -> Platform:
    return self._platform

  @property
  def path(self) -> pth.AnyPath | None:
    return self._path

  @property
  def local_path(self) -> pth.LocalPath | None:
    if path := self.path:
      return self.platform.local_path(path)
    return None

  def candidates(self) -> tuple[pth.AnyPath, ...]:
    return ()

  def _find_path(self) -> pth.AnyPath | None:
    for candidate_path in self._iterate_candidates():
      if self.is_valid_path(candidate_path):
        return candidate_path
    return self._find_fallback_path()

  def _iterate_candidates(self) -> Iterator[pth.AnyPath]:
    yield from self.candidates()

  def _find_fallback_path(self) -> pth.AnyPath | None:
    return None

  @abc.abstractmethod
  def is_valid_path(self, candidate: pth.AnyPath) -> bool:
    pass


def default_chromium_candidates(platform: Platform) -> tuple[pth.AnyPath, ...]:
  """Returns a generous list of potential locations of a chromium checkout."""
  candidates = []
  if chromium_src := platform.environ.get("CHROMIUM_SRC"):
    candidates.append(platform.path(chromium_src))
  if platform.is_local:
    candidates.append(chromium_src_relative_local_path())
  if platform.is_android:
    return tuple(candidates)
  home_dir = platform.home()
  candidates += [
      home_dir / "Documents/chromium/src",
      home_dir / "workspace/chromium/src",
      home_dir / "chromium/src",
      platform.path("C:/src/chromium/src"),
      home_dir / "Documents/chrome/src",
      home_dir / "workspace/chrome/src",
      home_dir / "chrome/src",
      platform.path("C:/src/chrome/src"),
  ]
  return tuple(candidates)


def chromium_src_relative_local_path() -> pth.LocalPath:
  """Gets the local relative path of `chromium/src`.

  Assuming the cli.py path is `third_party/crossbench/crossbench/cli/cli.py`.
  """
  return pth.LocalPath(__file__).parents[4]


def is_chromium_checkout_dir(platform: Platform, dir_path: pth.AnyPath) -> bool:
  return (platform.is_dir(dir_path / "v8") and
          platform.is_dir(dir_path / "chrome") and
          platform.is_dir(dir_path / ".git"))


class ChromiumCheckoutFinder(BasePathFinder):
  """Finds a chromium src checkout at either given locations or at
  some preset known checkout locations."""

  @override
  def candidates(self) -> tuple[pth.AnyPath, ...]:
    return default_chromium_candidates(self.platform)

  @override
  def is_valid_path(self, candidate: pth.AnyPath) -> bool:
    return is_chromium_checkout_dir(self.platform, candidate)
