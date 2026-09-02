# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Never, Sequence

import colorama
from typing_extensions import Self, override

from crossbench.cli.ui import ui


class CBNamespace(argparse.Namespace):
  """Namespace that can be frozen in-place to prevent mutations after setup."""

  _is_frozen: bool

  def __init__(self, **kwargs: Any) -> None:
    # Avoid AttributeError in __setattr__ before _is_frozen is set.
    super().__setattr__("_is_frozen", False)
    super().__init__(**kwargs)

  def freeze(self) -> Self:
    if self._is_frozen:
      return self
    for value in vars(self).values():
      if isinstance(value, CBNamespace):
        value.freeze()
    self._is_frozen = True
    return self

  def __setattr__(self, name: str, value: Any) -> None:
    if self._is_frozen:
      raise TypeError(f"Cannot modify immutable {type(self).__name__}: "
                      f"attempted to set {name}={value!r}")
    super().__setattr__(name, value)

  def __delattr__(self, name: str) -> None:
    if self._is_frozen:
      raise TypeError(f"Cannot delete attribute {name!r} from immutable "
                      f"{type(self).__name__}")
    super().__delattr__(name)


class CBArgumentParser(argparse.ArgumentParser):
  """Disables flag abbreviation and exit-on-error, and emits CBNamespace."""

  def __init__(self, **kwargs) -> None:
    kwargs["exit_on_error"] = False
    allow_abbrev = kwargs.pop("allow_abbrev", False)
    super().__init__(allow_abbrev=allow_abbrev, **kwargs)

  @override
  def parse_known_args(  # type: ignore[override]
      self,
      args: Sequence[str] | None = None,
      namespace: argparse.Namespace
      | None = None,
  ) -> tuple[CBNamespace, list[str]]:
    if namespace is None:
      namespace = CBNamespace()
    parsed_namespace, unprocessed = super().parse_known_args(
        args=args, namespace=namespace)
    assert isinstance(parsed_namespace, CBNamespace)
    return parsed_namespace, unprocessed

  @override
  def parse_args(  # type: ignore[override]
      self,
      args: Sequence[str] | None = None,
      namespace: argparse.Namespace | None = None,
  ) -> CBNamespace:
    if namespace is None:
      namespace = CBNamespace()
    parsed_namespace = super().parse_args(args=args, namespace=namespace)
    assert isinstance(parsed_namespace, CBNamespace)
    return parsed_namespace

  def fail(self, message: str) -> None:
    super().error(message)

  def exit(self, status: int = 0, message: str | None = None) -> Never:
    if message:
      if status == 0:
        logging.info(message)
      else:
        # Hack to get red colored output
        if ui.COLOR_LOGGING:
          print(str(colorama.Fore.RED))
        logging.critical(message)
        if ui.COLOR_LOGGING:
          print(str(colorama.Style.RESET_ALL))
    sys.exit(status)
