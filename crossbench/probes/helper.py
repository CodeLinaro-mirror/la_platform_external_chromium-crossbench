# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations
import csv

import pathlib
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from crossbench.platform import Platform

KeyFnType = Callable[[Tuple[str, ...]], Optional[str]]


def _default_flatten_key_fn(path: Tuple[str, ...]) -> str:
  return "/".join(path)


class Flatten:
  """
  Creates a sorted flat list of (key-path, Metric) from hierarchical data.

  input = {"a" : {"aa1":1, "aa2":2}, "b": 12 }
  Flatten(input).data == {
    "a/aa1":  1,
    "a/aa2":  2,
    "b":     12,
  }
  """
  _key_fn: KeyFnType
  _accumulator: Dict[str, Any]

  def __init__(self, *args: Dict, key_fn: Optional[KeyFnType] = None):
    """_summary_

    Args:
        *args (optional): Optional hierarchical data to be flattened
        key_fn (optional): Maps property paths (Tuple[str,...]) to strings used
          as final result keys, or None to skip property paths.
    """
    self._accumulator = {}
    self._key_fn = key_fn or _default_flatten_key_fn
    self.append(*args)

  @property
  def data(self) -> Dict[str, Any]:
    items = sorted(self._accumulator.items(), key=lambda item: item[0])
    return dict(items)

  def append(self, *args: Dict, ignore_toplevel: bool = False) -> None:
    toplevel_path: Tuple[str, ...] = tuple()
    for merged_data in args:
      self._flatten(toplevel_path, merged_data, ignore_toplevel)

  def _is_leaf_item(self, item: Any) -> bool:
    if isinstance(item, (str, float, int, list)):
      return True
    if "values" in item and isinstance(item["values"], list):
      return True
    return False

  def _flatten(self,
               parent_path: Tuple[str, ...],
               data,
               ignore_toplevel: bool = False) -> None:
    for name, item in data.items():
      path = parent_path + (name,)
      if self._is_leaf_item(item):
        if ignore_toplevel and parent_path == ():
          continue
        key = self._key_fn(path)
        if key is None:
          continue
        assert isinstance(key, str)
        if key in self._accumulator:
          raise ValueError(f"Duplicate key='{key}' path={path}")
        self._accumulator[key] = item
      else:
        self._flatten(path, item)

def _ljust(sequence: List, n: int, fillvalue: Any = "") -> List:
  return sequence + ([fillvalue] * (n - len(sequence)))


def merge_csv(csv_list: Sequence[pathlib.Path],
              headers: Optional[List[str]] = None,
              delimiter: str = "\t") -> List[List[Any]]:
  """
  Merge multiple CSV files.
  File 1:
    Header,     Col Header 1.1, Col Header  1.2
    Row Header, Data 1.1,       Data 1.2
  File 2:
    Header,     Col Header 2.1, Col Header 2.2
    Row Header, Data 2.1,       Data 2.2

  The first Col has to contain the same data:

  Merged:
    Header,     Col Header 1.1, Col Header 1.2,  Col Header 2.1, Col Header 2.2
    Row Header, Data 1.1,       Data 1.2,        Data 2.1,       Data 2.2


  If no column header is available, filename_as_header=True can be used.

  Merged with file name header:
            , File 1,           , File 2,
  Row Header, Data 1.1, Data 1.2, Data 2.1, Data 2.2
  """
  # Fill in the header column taken from the first file
  table: List[List[Any]] = []
  if headers:
    table_headers = [""]
  else:
    table_headers = []
  with csv_list[0].open(encoding="utf-8") as first_file:
    for row in csv.reader(first_file, delimiter=delimiter):
      assert row, "Mergeable CSV files musth have row names."
      metric_name = row[0]
      table.append([metric_name])

  for csv_file in csv_list:
    with csv_file.open(encoding="utf-8") as f:
      csv_data = list(csv.reader(f, delimiter=delimiter))
      # Find the max width
      max_rows_with_row_header = max(len(row) for row in csv_data)
      max_rows = max_rows_with_row_header - 1
      if headers:
        col_header = [headers.pop(0)]
        table_headers.extend(_ljust(col_header, max_rows))
      for table_row, row in zip(table, csv_data):
        metric_name = row[0]
        padded_row = _ljust(row[1:], max_rows)
        assert table_row[0] == metric_name, (f"{table_row[0]} != {metric_name}"
                                             f"\n{csv_data}\n{table}")
        table_row.extend(padded_row)

  if table_headers:
    return [table_headers] + table
  return table


class V8CheckoutFinder:

  def __init__(self, platform: Platform) -> None:
    self.platform = platform
    # A generous list of potential locations of a V8 or chromium checkout
    self.checkout_candidates = [
        # Assume crossbench is in chrome's src/third_party/crossbench
        pathlib.Path(__file__).parents[3] / "v8",
        # V8 Checkouts
        pathlib.Path.home() / "Documents/v8/v8",
        pathlib.Path.home() / "v8/v8",
        pathlib.Path("C:") / "src/v8/v8",
        # Raw V8 checkouts
        pathlib.Path.home() / "Documents/v8",
        pathlib.Path.home() / "v8",
        pathlib.Path("C:") / "src/v8/",
        # V8 in chromium checkouts
        pathlib.Path.home() / "Documents/chromium/src/v8",
        pathlib.Path.home() / "chromium/src/v8",
        pathlib.Path("C:") / "src/chromium/src/v8",
        # Chromium checkouts
        pathlib.Path.home() / "Documents/chromium/src",
        pathlib.Path.home() / "chromium/src",
        pathlib.Path("C:") / "src/chromium/src",
    ]
    self.v8_checkout: Optional[pathlib.Path] = self._find_v8_checkout()

  def _find_v8_checkout(self) -> Optional[pathlib.Path]:
    # Try potential build location
    for candidate_dir in self.checkout_candidates:
      if self._is_checkout_dir(candidate_dir):
        return candidate_dir
    maybe_d8_path = self.platform.environ.get("D8_PATH")
    if not maybe_d8_path:
      return None
    for candidate_dir in pathlib.Path(maybe_d8_path).parents:
      if self._is_checkout_dir(candidate_dir):
        return candidate_dir
    return None

  def _is_checkout_dir(self, candidate_dir: pathlib.Path) -> bool:
    v8_header_file = candidate_dir / "include" / "v8.h"
    git_dir = candidate_dir / ".git"
    return self.platform.is_file(v8_header_file) and (
        self.platform.is_dir(git_dir))
