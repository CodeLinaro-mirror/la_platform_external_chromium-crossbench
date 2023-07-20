# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import math
import pathlib
import re
import sys
from typing import Any, Iterator, Union

import hjson


def parse_path(str_value: str) -> pathlib.Path:
  try:
    path = pathlib.Path(str_value).expanduser()
  except RuntimeError as e:
    raise argparse.ArgumentTypeError(f"Invalid Path '{str_value}': {e}") from e
  if not path.exists():
    raise argparse.ArgumentTypeError(f"Path '{path}' does not exist.")
  return path


def parse_existing_file_path(str_value: str) -> pathlib.Path:
  path = parse_path(str_value)
  if not path.is_file():
    raise argparse.ArgumentTypeError(f"Path '{path}' is not a file.")
  return path


def parse_non_empty_file_path(str_value: str) -> pathlib.Path:
  path: pathlib.Path = parse_existing_file_path(str_value)
  if path.stat().st_size == 0:
    raise argparse.ArgumentTypeError(f"Path '{path}' is empty.")
  return path


def parse_file_path(str_value: str) -> pathlib.Path:
  return parse_non_empty_file_path(str_value)


def parse_dir_path(str_value: str) -> pathlib.Path:
  path = parse_path(str_value)
  if not path.is_dir():
    raise argparse.ArgumentTypeError(f"Path '{path}', is not a file.")
  return path


def parse_json_file_path(str_value: str) -> pathlib.Path:
  path = parse_file_path(str_value)
  with path.open(encoding="utf-8") as f:
    try:
      json.load(f)
    except ValueError as e:
      raise argparse.ArgumentTypeError(f"Invalid json file: {path}: {e}") from e
  return path


def parse_hjson_file_path(str_value: str) -> pathlib.Path:
  path = parse_file_path(str_value)
  with path.open(encoding="utf-8") as f:
    try:
      hjson.load(f)
    except ValueError as e:
      raise argparse.ArgumentTypeError(
          f"Invalid {hjson.__name__} file: {path}: {e}") from e
  return path


def parse_json_file(str_value: str) -> Any:
  path = parse_file_path(str_value)
  with path.open(encoding="utf-8") as f:
    return json.load(f)


def parse_positive_float(value: str) -> float:
  value_f = float(value)
  if not math.isfinite(value_f) or value_f < 0:
    raise argparse.ArgumentTypeError(
        f"Expected positive value, but got: {value_f}")
  return value_f


def parse_positive_zero_int(value: str) -> int:
  positive_int = int(value)
  if positive_int < 0:
    raise argparse.ArgumentTypeError(
        f"Expected int >= 0, but got: {positive_int}")
  return positive_int


def parse_positive_int(value: str, msg: str = "") -> int:
  value_i = int(value)
  if not math.isfinite(value_i) or value_i < 0:
    raise argparse.ArgumentTypeError(
        f"Expected int > 0 {msg},but got: {value_i}")
  return value_i


class CrossBenchArgumentError(argparse.ArgumentError):
  """Custom class that also prints the argument.help if available.
  """

  def __init__(self, argument: Any, message: str) -> None:
    self.help: str = ""
    super().__init__(argument, message)
    if self.argument_name:
      self.help = getattr(argument, "help", "")

  def __str__(self) -> str:
    formatted = super().__str__()
    if not self.help:
      return formatted
    return (f"argument error {self.argument_name}:\n\n"
            f"Help {self.argument_name}:\n{self.help}\n\n"
            f"{formatted}")


# Needed to gap the diff between 3.8 and 3.9 default args that change throwing
# behavior.
class _BaseCrossBenchArgumentParser(argparse.ArgumentParser):

  def fail(self, message):
    super().error(message)


if sys.version_info < (3, 9, 0):

  class CrossBenchArgumentParser(_BaseCrossBenchArgumentParser):

    def error(self, message):
      # Let the CrossBenchCLI handle all errors and simplify testing.
      exception = sys.exc_info()[1]
      if isinstance(exception, BaseException):
        raise exception
      raise argparse.ArgumentError(None, message)

else:

  class CrossBenchArgumentParser(_BaseCrossBenchArgumentParser):

    def __init__(self, *args, **kwargs):
      kwargs["exit_on_error"] = False
      super().__init__(*args, **kwargs)


class LateArgumentError(argparse.ArgumentTypeError):
  """Signals argument parse errors after parser.parse_args().
  This is used to map errors back to the original argument, much like
  argparse.ArgumentError does internally. However, since this happens after
  the internal argument parsing we need this custom implementation to print
  more descriptive error messages.
  """

  def __init__(self, flag: str, message: str):
    super().__init__(message)
    self.flag = flag
    self.message = message


@contextlib.contextmanager
def late_argument_type_error_wrapper(flag: str) -> Iterator[None]:
  """Converts raised ValueError and ArgumentTypeError to LateArgumentError
  that are associated with the given flag.
  """
  try:
    yield
  except (ValueError, argparse.ArgumentTypeError) as e:
    raise LateArgumentError(flag, str(e)) from e


class Duration:
  _DURATION_RE = re.compile(r"(?P<value>(\d+(\.\d+)?)) ?(?P<unit>[^0-9\.]+)?")

  @classmethod
  def _to_timedelta(cls, value: float, suffix: str) -> dt.timedelta:
    if suffix in {"ms", "millis", "milliseconds"}:
      return dt.timedelta(milliseconds=value)
    if suffix in {"s", "sec", "secs", "second", "seconds"}:
      return dt.timedelta(seconds=value)
    if suffix in {"m", "min", "mins", "minute", "minutes"}:
      return dt.timedelta(minutes=value)
    if suffix in {"h", "hrs", "hour", "hours"}:
      return dt.timedelta(hours=value)
    raise ValueError(f"Error: {suffix} is not support for duration. "
                     "Make sure to use a supported time unit/suffix")

  @classmethod
  def parse(cls, time_value: Union[float, int, str]) -> dt.timedelta:
    """
    This function will parse the measurement and the value from string value.

    For example:
    5s => dt.timedelta(seconds=5)
    5m => 5*60 = dt.timedelta(minutes=5)

    """
    if isinstance(time_value, (int, float)):
      if time_value < 0:
        raise argparse.ArgumentTypeError(
            f"Duration must be positive, but got: {time_value}")
      return dt.timedelta(seconds=time_value)

    if not time_value:
      raise argparse.ArgumentTypeError("duration.")

    match = cls._DURATION_RE.fullmatch(time_value)
    if match is None:
      raise argparse.ArgumentTypeError(
          f"Unknown Duration format: '{time_value}'")

    value = match.group("value")
    if not value:
      raise argparse.ArgumentTypeError(
          "Error: Duration value not found."
          f"Make sure to include a valid duration value: '{time_value}'")
    time_unit = match.group("unit")
    try:
      time_value = float(value)
    except ValueError as e:
      raise argparse.ArgumentTypeError(f"Duration must be a valid number, {e}")
    if time_value < 0 or math.isnan(time_value) or math.isinf(time_value):
      raise argparse.ArgumentTypeError(
          f"Duration must be positive, but got: {time_value}")

    if not time_unit:
      # If no time unit provided we assume it is in seconds.
      return dt.timedelta(seconds=time_value)
    return cls._to_timedelta(time_value, time_unit)
