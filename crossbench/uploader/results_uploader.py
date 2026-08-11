# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import functools
import logging
import os
import tarfile
import tempfile
import uuid
from typing import TYPE_CHECKING

from crossbench import path as pth
from crossbench.parse import ObjectParser
from crossbench.uploader.gcs import GoogleCloudStorageUploader

if TYPE_CHECKING:
  from crossbench.uploader.base import BaseUploader

_SCHEME_TO_UPLOADER: dict[str, type[BaseUploader]] = {
    "gs": GoogleCloudStorageUploader,
}


def upload(source: pth.LocalPath, target: str) -> str | None:
  """Zips source directory and uploads the archive to target URL."""

  uploader = _uploader_for_url(target)

  with tempfile.TemporaryDirectory() as tmp_dirname:
    logging.critical("📦 ZIP RESULTS: Zipping %s", source)
    archive_path = _create_archive(source, pth.LocalPath(tmp_dirname))

    logging.critical("📤 UPLOAD RESULTS: Uploading %s", archive_path)
    try:
      result_url = uploader.upload(archive_path)
    except (RuntimeError, ValueError, OSError) as e:
      logging.error("Failed to upload results: %s", e)
      return None

    logging.critical("☁️ UPLOAD RESULTS FINISHED: %s", result_url)
    return result_url


def supported_schemes_str() -> str:
  return ", ".join(f"{scheme}://" for scheme in _SCHEME_TO_UPLOADER)


def target_url(url: str) -> str:
  """Validates that url is a supported results upload destination URL."""
  if not url:
    url = os.environ.get("CROSSBENCH_RESULT_UPLOAD_TARGET", "")
    if not url:
      raise argparse.ArgumentTypeError(
          "--upload-results specified without value, but "
          "CROSSBENCH_RESULT_UPLOAD_TARGET environment variable is not set.")
  return ObjectParser.url_str(
      url, name="results upload URL", schemes=tuple(_SCHEME_TO_UPLOADER.keys()))


def _uploader_for_url(url: str) -> BaseUploader:
  scheme = ObjectParser.base_url(url).scheme
  if uploader_cls := _SCHEME_TO_UPLOADER.get(scheme):
    return uploader_cls(url=url)
  raise ValueError(f"Unsupported upload URL scheme: {url!r}")


def _create_archive(source_dir: pth.LocalPath,
                    dest_dir: pth.LocalPath) -> pth.LocalPath:
  """Creates a compressed tarball of source_dir in dest_dir."""
  archive_id = str(uuid.uuid4())
  archive_path = dest_dir / f"{archive_id}.tar.gz"
  tar_filter = functools.partial(
      _filter_tarinfo, source_dir=source_dir, archive_id=archive_id)
  with tarfile.open(archive_path, "w:gz") as tar:
    tar.add(source_dir, arcname=archive_id, filter=tar_filter)
  return archive_path


def _filter_tarinfo(tarinfo: tarfile.TarInfo, source_dir: pth.LocalPath,
                    archive_id: str) -> tarfile.TarInfo:
  """Rewrites internal absolute symlinks into relative paths for portability."""
  if tarinfo.issym() or tarinfo.islnk():
    relative_name = pth.LocalPath(tarinfo.name).relative_to(archive_id)
    symlink_file = source_dir / relative_name
    target_path = (symlink_file.parent / tarinfo.linkname).resolve()
    if target_path == source_dir or target_path.is_relative_to(source_dir):
      tarinfo.linkname = os.path.relpath(target_path, symlink_file.parent)
  return tarinfo
