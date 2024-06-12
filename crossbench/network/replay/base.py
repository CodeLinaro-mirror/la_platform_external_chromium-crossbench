# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import contextlib
import hashlib
import logging
import re
from typing import TYPE_CHECKING, Iterator, Optional
from urllib.parse import urlparse

from crossbench import cli_helper, plt
from crossbench import path as pth
from crossbench.network.base import Network, TrafficShaper
from crossbench.runner.groups.session import BrowserSessionRunGroup

if TYPE_CHECKING:
  from crossbench.path import LocalPath


GS_PREFIX = "gs://"
WPR_CACHE = pth.LocalPath(__file__).parents[3] / "wpr_cache"


class ReplayNetwork(Network):
  """ A network implementation that can be used to replay requests
  from a an archive."""

  def __init__(self,
               archive_path_or_url: str,
               traffic_shaper: Optional[TrafficShaper] = None,
               browser_platform: plt.Platform = plt.PLATFORM):
    super().__init__(traffic_shaper, browser_platform)
    self._ensure_archive(archive_path_or_url)

  @property
  def archive_path(self) -> LocalPath:
    return self._archive_path

  @contextlib.contextmanager
  def open(self, session: BrowserSessionRunGroup) -> Iterator[ReplayNetwork]:
    with super().open(session):
      with self._open_replay_server(session):
        with self._traffic_shaper.open(self, session):
          yield self

  @contextlib.contextmanager
  def _open_replay_server(self, session: BrowserSessionRunGroup):
    del session
    yield

  def _generate_filename(self, url: str) -> str:
    metadata = self.runner_platform.sh_stdout("gsutil", "ls", "-L", url)
    md5_regex = re.compile(r"Hash \(md5\):\s*(.*)==")
    md5 = md5_regex.search(metadata).group(1)
    filesafe_md5 = md5.translate(str.maketrans("\\/", "__"))
    remote_path = pth.RemotePath(urlparse(url).path)
    return f"{remote_path.stem}_{filesafe_md5}{remote_path.suffix}"

  def _download_gcloud_archive(self, url: str) -> LocalPath:
    WPR_CACHE.mkdir(parents=True, exist_ok=True)
    local_path = WPR_CACHE / self._generate_filename(url)
    if local_path.is_file():
      logging.info("Found cached WPR archive: %s", local_path)
    else:
      logging.info("Downloading WPR archive from %s to %s", url, local_path)
      self.runner_platform.sh("gsutil", "cp", url, local_path)
    return local_path

  def _ensure_archive(self, archive_path_or_url: str):
    if archive_path_or_url.startswith(GS_PREFIX):
      archive_path_or_url = self._download_gcloud_archive(archive_path_or_url)
    self._archive_path = cli_helper.parse_existing_file_path(
          archive_path_or_url).resolve()
