# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench import plt
from crossbench.uploader.base import BaseUploader

if TYPE_CHECKING:
  from crossbench import path as pth


class GoogleCloudStorageUploader(BaseUploader):
  """Uploads files to Google Cloud Storage (GCS)."""

  def __init__(self, url: str) -> None:
    super().__init__(url)
    assert self._url.startswith("gs://")

  @override
  def upload(self, file_path: pth.LocalPath) -> str:
    gcloud_bin = plt.PLATFORM.which("gcloud")
    if not gcloud_bin:
      raise RuntimeError("Could not find 'gcloud' executable in PATH.")
    dest_url = f"{self._url.rstrip('/')}/{file_path.name}"

    res = plt.PLATFORM.sh(
        gcloud_bin,
        "storage",
        "cp",
        file_path,
        dest_url,
        capture_output=True,
        check=False,
    )
    if res.returncode != 0:
      raise RuntimeError(f"gs upload failure: ({res.returncode}): {res.stderr}")

    return dest_url
