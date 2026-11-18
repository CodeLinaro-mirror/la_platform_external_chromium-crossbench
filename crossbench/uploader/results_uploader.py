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
from typing import TYPE_CHECKING, Final

from crossbench import path as pth
from crossbench.parse import PathParser
from crossbench.probes.internal.summary import ResultsSummaryProbe
from crossbench.uploader.gcs import GoogleCloudStorageUploader
from crossbench.uploader.gdrive import GoogleDriveUploader

if TYPE_CHECKING:
  from crossbench.uploader.base import BaseUploader

_UPLOADERS: Final[tuple[type[BaseUploader], ...]] = (
  GoogleCloudStorageUploader,
  GoogleDriveUploader,
)


def result_dir(value: pth.LocalPathLike) -> pth.LocalPath:
  """Validates that value points to a valid Crossbench result directory."""
  path = PathParser.path(value)
  try:
    path = path.resolve()
  except (RuntimeError, OSError) as e:
    raise argparse.ArgumentTypeError(
      f"Failed to resolve path {str(path)!r}: {e}"
    ) from e
  if not path.exists():
    raise argparse.ArgumentTypeError(f"Path does not exist: {str(path)!r}")
  if not path.is_dir():
    raise argparse.ArgumentTypeError(
      f"Result path must be a directory, not a file: {str(path)!r}"
    )
  if not _is_result_dir(path):
    raise argparse.ArgumentTypeError(
      f"Path is not a valid Crossbench result directory: {str(path)!r} "
      f"(missing {ResultsSummaryProbe.FILE_NAME!r})."
    )
  return path


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


def supported_targets_str() -> str:
  """Human-readable list of all supported upload target formats."""
  return ", ".join(
    target_format
    for uploader_cls in _UPLOADERS
    for target_format in uploader_cls.TARGET_FORMATS
  )


def target_url(url: str) -> str:
  """Validates and normalizes a results upload destination."""
  if not url:
    url = os.environ.get("CROSSBENCH_RESULT_UPLOAD_TARGET", "")
    if not url:
      raise argparse.ArgumentTypeError(
        "Target upload URL not specified, and "
        "CROSSBENCH_RESULT_UPLOAD_TARGET environment variable is not set."
      )
  for uploader_cls in _UPLOADERS:
    if canonical := uploader_cls.parse_target(url):
      return canonical
  raise argparse.ArgumentTypeError(
    f"Unsupported results upload target: {url!r}. "
    f"Supported formats: {supported_targets_str()}."
  )


def _is_result_dir(path: pth.LocalPath) -> bool:
  """Heuristically checks if a directory is a Crossbench result directory.

  Crossbench generates a 'cb.results.json' summary file at the root of the
  results output directory upon benchmark completion. Note that this is only
  a heuristic - any folder could happen to contain a file with this name, and
  future or past versions of Crossbench might produce different files.
  """
  return (path / ResultsSummaryProbe.FILE_NAME).is_file()


def _uploader_for_url(url: str) -> BaseUploader:
  for uploader_cls in _UPLOADERS:
    try:
      if canonical := uploader_cls.parse_target(url):
        return uploader_cls(url=canonical)
    except argparse.ArgumentTypeError as e:
      raise ValueError(str(e)) from e
  raise ValueError(f"Unsupported upload target: {url!r}")


def _create_archive(
  source_dir: pth.LocalPath, dest_dir: pth.LocalPath
) -> pth.LocalPath:
  """Creates a compressed tarball of source_dir in dest_dir."""
  archive_id = str(uuid.uuid4())
  archive_path = dest_dir / f"{archive_id}.tar.gz"
  tar_filter = functools.partial(
    _filter_tarinfo, source_dir=source_dir, archive_id=archive_id
  )
  with tarfile.open(archive_path, "w:gz") as tar:
    tar.add(source_dir, arcname=archive_id, filter=tar_filter)
  return archive_path


def _filter_tarinfo(
  tarinfo: tarfile.TarInfo, source_dir: pth.LocalPath, archive_id: str
) -> tarfile.TarInfo:
  """Rewrites internal absolute symlinks into relative paths for portability."""
  if tarinfo.issym() or tarinfo.islnk():
    relative_name = pth.LocalPath(tarinfo.name).relative_to(archive_id)
    symlink_file = source_dir / relative_name
    target_path = (symlink_file.parent / tarinfo.linkname).resolve()
    if target_path == source_dir or target_path.is_relative_to(source_dir):
      tarinfo.linkname = os.path.relpath(target_path, symlink_file.parent)
  return tarinfo
