# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import enum


class BrowserAttributes(enum.Flag):
  SAFARI = enum.auto()
  FIREFOX = enum.auto()
  CHROMIUM = enum.auto()
  CHROME = enum.auto()
  EDGE = enum.auto()

  CHROMIUM_BASED = enum.auto()

  WEBDRIVER = enum.auto()
  APPLESCRIPT = enum.auto()

  MOBILE = enum.auto()
  DESKTOP = enum.auto()

  REMOTE = enum.auto()

  @property
  def is_chromium_based(self) -> bool:
    return self.CHROMIUM_BASED in self

  @property
  def is_chrome(self) -> bool:
    return self.CHROME in self

  @property
  def is_safari(self) -> bool:
    return self.SAFARI in self

  @property
  def is_edge(self) -> bool:
    return self.EDGE in self

  @property
  def is_firefox(self) -> bool:
    return self.FIREFOX in self
