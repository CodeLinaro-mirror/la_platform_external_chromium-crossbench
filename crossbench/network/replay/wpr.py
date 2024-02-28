# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import contextlib
import logging
import pathlib
from typing import TYPE_CHECKING, Optional

from crossbench import cli_helper
from crossbench.flags import Flags
from crossbench.helper.path_finder import WprGoToolFinder
from crossbench.network.replay.base import ReplayNetwork
from crossbench.network.replay.web_page_replay import WprReplayServer
from crossbench.plt import PLATFORM, Platform

if TYPE_CHECKING:
  from crossbench.browsers.browser import Browser
  from crossbench.network.base import TrafficShaper
  from crossbench.runner.groups.session import BrowserSessionRunGroup


class WprReplayNetwork(ReplayNetwork):

  def __init__(self,
               archive_path: pathlib.Path,
               traffic_shaper: Optional[TrafficShaper] = None,
               wpr_go_bin: Optional[pathlib.Path] = None,
               runner_platform: Platform = PLATFORM):
    super().__init__(archive_path, traffic_shaper, runner_platform)
    if not wpr_go_bin:
      wpr_go_bin = WprGoToolFinder(runner_platform).path
    self._wpr_go_bin = cli_helper.parse_binary_path(wpr_go_bin, "wpr.go source")
    self._server: Optional[WprReplayServer] = None

  def extra_flags(self, browser: Browser) -> Flags:
    assert self.is_running, "Extra network flags are not valid"
    assert self._server
    if not browser.attributes.is_chromium_based:
      raise ValueError(
          "Only chromium-based browsers are supported for wpr replay.")
    return Flags({
        "--host-resolver-rules":
            (f"MAP *:80 127.0.0.1:{self._server.http_port},"
             f"MAP *:443 127.0.0.1:{self._server.https_port},"
             "EXCLUDE localhost"),
        # TODO: read this from wpr_public_hash.txt like in the recoder probe
        "--ignore-certificate-errors-spki-list":
            ("PhrPvGIaAMmd29hj8BCZOq096yj7uMpRNHpn5PDxI6I=,"
             "2HcXCSKKJS0lEXLQEWhpHUfGuojiU0tiT5gOF9LP6IQ=")
    })

  @contextlib.contextmanager
  def _open_replay_sever(self, session: BrowserSessionRunGroup):
    self._server = WprReplayServer(
        self.archive_path,
        self._wpr_go_bin,
        http_port=8080,
        https_port=8081,
        log_path=session.out_dir / "network.wpr.log")
    logging.debug("Starting WPR server")
    try:
      self._server.start()
      yield self
    finally:
      self._server.stop()

  def __str__(self) -> str:
    return f"WPR(archive={self.archive_path}, traffic={self.traffic_shaper})"
