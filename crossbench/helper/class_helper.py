# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import inspect


def get_all_subclasses(cls: type) -> set:
  """Recursively gets all subclasses of a given class."""
  all_subclasses = set()
  for subclass in cls.__subclasses__():
    if not inspect.isabstract(subclass):
      all_subclasses.add(subclass)
    all_subclasses.update(get_all_subclasses(subclass))
  return all_subclasses
