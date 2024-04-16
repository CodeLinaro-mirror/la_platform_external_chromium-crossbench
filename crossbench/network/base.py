# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import contextlib
from typing import TYPE_CHECKING, Iterator, Optional

from crossbench import plt
from crossbench.flags import Flags

if TYPE_CHECKING:
  from crossbench.browsers.browser import Browser
  from crossbench.runner.groups.session import BrowserSessionRunGroup


class TrafficShaper(abc.ABC):

  @contextlib.contextmanager
  @abc.abstractmethod
  def open(self, network: Network,
           session: BrowserSessionRunGroup) -> Iterator[TrafficShaper]:
    pass


class NoTrafficShaper(TrafficShaper):

  @contextlib.contextmanager
  def open(self, network: Network,
           session: BrowserSessionRunGroup) -> Iterator[TrafficShaper]:
    del network, session
    yield self

  def __str__(self) -> str:
    return "full"



class Network(abc.ABC):

  def __init__(self,
               traffic_shaper: Optional[TrafficShaper] = None,
               runner_platform: plt.Platform = plt.PLATFORM) -> None:
    self._traffic_shaper = traffic_shaper or NoTrafficShaper()
    self._runner_platform = runner_platform
    self._is_running: bool = False

  @property
  def traffic_shaper(self) -> TrafficShaper:
    return self._traffic_shaper

  @property
  def runner_platform(self) -> plt.Platform:
    return self._runner_platform

  @property
  def is_running(self) -> bool:
    return self._is_running

  def extra_flags(self, browser: Browser) -> Flags:
    del browser
    assert self.is_running, "Network is not running."
    return Flags()

  @contextlib.contextmanager
  def open(self, session: BrowserSessionRunGroup) -> Iterator[Network]:
    del session
    assert not self._is_running, "Cannot start network more than once."
    self._is_running = True
    try:
      yield self
    finally:
      self._is_running = False
