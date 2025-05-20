# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING

from crossbench.network.local_file_server import LocalFileNetwork

if TYPE_CHECKING:
  import crossbench.path as pth
  from crossbench.browsers.d8.d8 import D8
  from crossbench.network.base import Network


class D8URLMapper:

  def __init__(self, d8: D8):
    self._d8 = d8
    network: Network = d8.network
    assert isinstance(
        network, LocalFileNetwork), (f"Expected LocalFileNetwork got {network}")
    self._network: LocalFileNetwork = network

  @property
  def path(self) -> pth.LocalPath:
    return self._network.path

  def lookup(self, url: str) -> pth.LocalPath | None:
    if "jetstream" in str(self.path).lower() or "jetstream" in url:
      return self.path / "JetStreamDriver.js"
    # TODO: support other benchmarks in the future
    return None
