# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from crossbench import path as pth
from crossbench import plt
from crossbench.browsers.splash_screen import SplashScreen
from crossbench.browsers.viewport import Viewport
from crossbench.flags.base import Flags
from crossbench.network.live import LiveNetwork

if TYPE_CHECKING:
  from crossbench.network.base import Network


class Settings:
  """Container object for browser agnostic settings."""

  def __init__(self,
               flags: Optional[Flags.InitialDataType] = None,
               js_flags: Optional[Flags.InitialDataType] = None,
               cache_dir: Optional[pth.RemotePath] = None,
               network: Optional[Network] = None,
               driver_path: Optional[pth.RemotePath] = None,
               viewport: Optional[Viewport] = None,
               splash_screen: Optional[SplashScreen] = None,
               platform: Optional[plt.Platform] = None):
    self._flags = Flags(flags) if flags else Flags()
    self._js_flags = Flags(js_flags) if js_flags else Flags()
    self._cache_dir = cache_dir
    self._platform = platform or plt.PLATFORM
    self._driver_path = driver_path
    self._network: Network = network or LiveNetwork()
    self._viewport: Viewport = viewport or Viewport.DEFAULT
    self._splash_screen: SplashScreen = splash_screen or SplashScreen.DEFAULT

  @property
  def flags(self) -> Flags:
    return self._flags

  @property
  def js_flags(self) -> Flags:
    return self._js_flags

  @property
  def cache_dir(self) -> Optional[pth.RemotePath]:
    return self._cache_dir

  @property
  def driver_path(self) -> Optional[pth.RemotePath]:
    return self._driver_path

  @property
  def platform(self) -> plt.Platform:
    return self._platform

  @property
  def network(self) -> Network:
    return self._network

  @property
  def splash_screen(self) -> SplashScreen:
    return self._splash_screen

  @property
  def viewport(self) -> Viewport:
    return self._viewport

  @viewport.setter
  def viewport(self, value: Viewport) -> None:
    assert self._viewport.is_default
    self._viewport = value
