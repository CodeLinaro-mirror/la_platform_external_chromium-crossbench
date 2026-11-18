# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, ClassVar, Final

if TYPE_CHECKING:
  from crossbench import path as pth


class BaseUploader(abc.ABC):
  # Human-readable target formats accepted by this uploader, for help texts.
  TARGET_FORMATS: ClassVar[tuple[str, ...]] = ()

  def __init__(self, url: str) -> None:
    self._url: Final[str] = url

  @classmethod
  @abc.abstractmethod
  def parse_target(cls, target: str) -> str:
    """Returns the canonical target string if this uploader handles target, or
    an empty string if target belongs to another uploader.

    Raises argparse.ArgumentTypeError if target matches this uploader's scheme
    or prefix, but is malformed (e.g. 'gs://').
    """

  @abc.abstractmethod
  def upload(self, file_path: pth.LocalPath) -> str:
    """Uploads file_path and returns the uploaded file URL/location."""
