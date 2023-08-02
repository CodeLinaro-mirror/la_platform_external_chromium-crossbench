# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import re
import tempfile
from typing import TYPE_CHECKING, Optional, Tuple

from crossbench import helper
from crossbench.browsers.browser import (Browser, BrowserVersion,
                                         BrowserVersionChannel)
from crossbench.browsers.viewport import Viewport
from crossbench.browsers.webdriver import WebDriverBrowser

if TYPE_CHECKING:
  from crossbench.browsers.splash_screen import SplashScreen
  from crossbench.flags import Flags
  from crossbench.platform import Platform
  from crossbench.runner import Run


class FirefoxVersion(BrowserVersion):
  _VERSION_RE = re.compile(r"[^\d]+ (?P<version>"
                           r"(?P<parts>\d+\.\d+(?P<channel>[ab.])\d+)"
                           r")(?P<channel_esr>esr)?")
  _SPLIT_RE = re.compile(r'[ab.]')
  _CHANNEL_LOOKUP = {
      "esr": (BrowserVersionChannel.LTS, 3),
      ".": (BrowserVersionChannel.STABLE, 2),
      # IRL Firefox version numbers do not distinct beta from stable, so we
      # remap Firefox Dev => beta.
      "b": (BrowserVersionChannel.BETA, 1),
      "a": (BrowserVersionChannel.ALPHA, 0),
  }

  def _parse(
      self,
      version: str,
  ) -> Tuple[Tuple[int, ...], BrowserVersionChannel, str]:
    matches = self._VERSION_RE.fullmatch(version.strip())
    if not matches:
      raise ValueError(f"Could not extract version number from '{version}'")
    version_str = matches["version"]
    version_parts = matches["parts"]
    assert version_parts and version_str
    if matches["channel_esr"] and matches["channel"] != ".":
      raise ValueError(f"Invalid ESR version: {version}")
    channel: str = (matches["channel_esr"] or matches["channel"] or
                    "stable").lower()
    browser_channel, channel_id = self._CHANNEL_LOOKUP[channel]
    parts = tuple(map(int, self._SPLIT_RE.split(version_parts)))
    if len(parts) != 3:
      raise ValueError(f"Invalid number of version number parts in '{version}'")
    # Inject browser_channel into the version parts to make it unique
    parts = parts[:-1] + (channel_id, parts[-1])
    return parts, browser_channel, version_str

  def _channel_name(self, channel: BrowserVersionChannel) -> str:
    if channel == BrowserVersionChannel.LTS:
      return "esr"
    if channel == BrowserVersionChannel.STABLE:
      return "stable"
    if channel == BrowserVersionChannel.BETA:
      return "dev"
    if channel == BrowserVersionChannel.ALPHA:
      return "nightly"
    raise ValueError(f"Unsupported channel: {channel}")


class Firefox(Browser):

  @classmethod
  def default_path(cls) -> pathlib.Path:
    return helper.search_app_or_executable(
        "Firefox",
        macos=["Firefox.app"],
        linux=["firefox"],
        win=["Mozilla Firefox/firefox.exe"])

  @classmethod
  def developer_edition_path(cls) -> pathlib.Path:
    return helper.search_app_or_executable(
        "Firefox Developer Edition",
        macos=["Firefox Developer Edition.app"],
        linux=["firefox-developer-edition"],
        win=["Firefox Developer Edition/firefox.exe"])

  @classmethod
  def nightly_path(cls) -> pathlib.Path:
    return helper.search_app_or_executable(
        "Firefox Nightly",
        macos=["Firefox Nightly.app"],
        linux=["firefox-nightly", "firefox-trunk"],
        win=["Firefox Nightly/firefox.exe"])

  def __init__(
      self,
      label: str,
      path: pathlib.Path,
      flags: Optional[Flags.InitialDataType] = None,
      js_flags: Optional[Flags.InitialDataType] = None,
      cache_dir: Optional[pathlib.Path] = None,
      type: str = "firefox",  # pylint: disable=redefined-builtin
      driver_path: Optional[pathlib.Path] = None,
      viewport: Optional[Viewport] = None,
      splash_screen: Optional[SplashScreen] = None,
      platform: Optional[Platform] = None):
    if cache_dir is None:
      # pylint: disable=bad-option-value, consider-using-with
      self.cache_dir = pathlib.Path(
          tempfile.TemporaryDirectory(prefix="firefox").name)
      self.clear_cache_dir = True
      self.cache_dir = cache_dir
      self.clear_cache_dir = False
    super().__init__(
        label,
        path,
        flags,
        js_flags=None,
        type=type,
        driver_path=driver_path,
        viewport=viewport,
        splash_screen=splash_screen,
        platform=platform)
    assert not js_flags, "Firefox doesn't support custom js_flags"

  def _extract_version(self) -> str:
    assert self.path
    version_string = self.platform.app_version(self.path)
    # "Firefox 107.0" => "107.0"
    return str(re.findall(r"[\d\.]+", version_string)[0])

  def _get_browser_flags_for_run(self, run: Run) -> Tuple[str, ...]:
    flags_copy = self.flags.copy()
    flags_copy.update(run.extra_flags)
    self._handle_viewport_flags(flags_copy)
    if self.cache_dir and self.cache_dir:
      flags_copy["--profile"] = str(self.cache_dir)
    if self.log_file:
      flags_copy["--MOZ_LOG_FILE"] = str(self.log_file)
    return tuple(flags_copy.get_list())

  def _handle_viewport_flags(self, flags: Flags) -> None:
    new_width, new_height = 0, 0
    if self.viewport.has_size:
      new_width, new_height = self.viewport.size
    update_size = False
    if "--width" in flags:
      if self.viewport.is_default:
        new_width = int(flags["--width"])
        update_size = True
      else:
        assert self.viewport.width == int(flags["--width"])
    if "--height" in flags:
      if self.viewport.is_default:
        new_height = int(flags["--height"])
        update_size = True
      else:
        assert self.viewport.height == int(flags["--height"])
    if update_size:
      assert self.viewport.is_default
      self.viewport = Viewport(new_width, new_height)
    elif self.viewport.has_size:
      flags["--width"] = str(self.viewport.width)
      flags["--height"] = str(self.viewport.height)

    self._sync_viewport_flag(flags, "--kiosk", self.viewport.is_fullscreen,
                             Viewport.FULLSCREEN)
    self._sync_viewport_flag(flags, "--headless", self.viewport.is_headless,
                             Viewport.HEADLESS)

    if self.viewport.has_size and not self.viewport.is_default:
      if not isinstance(self,
                        WebDriverBrowser) and self.viewport.size != (0, 0):
        raise ValueError(f"Browser {self} cannot handle viewport position: "
                         f"{self.viewport.position}")
    else:
      if not isinstance(self, WebDriverBrowser):
        raise ValueError(
            f"Browser {self} cannot handle viewport mode: {self.viewport}")
