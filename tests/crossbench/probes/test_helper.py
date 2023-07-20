# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import csv
import os
import pathlib
import sys
import unittest
from unittest import mock

import pyfakefs.fake_filesystem_unittest
import pytest

from crossbench.probes import helper
from tests.crossbench.mock_helper import BaseCrossbenchTestCase


class TestMergeCSV(pyfakefs.fake_filesystem_unittest.TestCase):

  def setUp(self):
    self.setUpPyfakefs()

  def test_merge_single(self):
    file = pathlib.Path("test.csv")
    data = [
        ["Metric", "Run1"],
        ["Total", "200"],
    ]
    for delimiter in ["\t", ","]:
      with file.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter=delimiter).writerows(data)
      merged = helper.merge_csv([file], delimiter=delimiter)
      self.assertListEqual(merged, data)

  def test_merge_single_padding(self):
    file = pathlib.Path("test.csv")
    data = [
        ["Metric", "Run1", "Run2"],
        ["marker"],
        ["Total", "200", "300"],
    ]
    with file.open("w", newline="", encoding="utf-8") as f:
      csv.writer(f, delimiter="\t").writerows(data)
    merged = helper.merge_csv([file], headers=None)
    self.assertListEqual(merged, [
        ["Metric", "Run1", "Run2"],
        ["marker", "", ""],
        ["Total", "200", "300"],
    ])

  def test_merge_single_file_header(self):
    file = pathlib.Path("test.csv")
    data = [
        ["Total", "200"],
    ]
    for delimiter in ["\t", ","]:
      with file.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter=delimiter).writerows(data)
      merged = helper.merge_csv([file],
                                delimiter=delimiter,
                                headers=[file.name])
      self.assertListEqual(merged, [
          ["", file.name],
          ["Total", "200"],
      ])

  def test_merge_two_padding(self):
    file_1 = pathlib.Path("test_1.csv")
    file_2 = pathlib.Path("test_2.csv")
    data_1 = [
        ["marker"],
        ["Total", "101", "102"],
    ]
    data_2 = [
        ["marker"],
        ["Total", "201"],
    ]
    with file_1.open("w", newline="", encoding="utf-8") as f:
      csv.writer(f, delimiter="\t").writerows(data_1)
    with file_2.open("w", newline="", encoding="utf-8") as f:
      csv.writer(f, delimiter="\t").writerows(data_2)
    merged = helper.merge_csv([file_1, file_2], headers=["col_1", "col_2"])
    self.assertListEqual(merged, [
        ["", "col_1", "", "col_2"],
        ["marker", "", "", ""],
        ["Total", "101", "102", "201"],
    ])


class TestFlatten(unittest.TestCase):

  def flatten(self, *data, key_fn=None):
    return helper.Flatten(*data, key_fn=key_fn).data

  def test_single(self):
    data = {
        "a": 1,
        "b": 2,
    }
    flattened = self.flatten(data)
    self.assertDictEqual(flattened, data)

  def test_single_nested(self):
    data = {
        "a": 1,
        "b": {
            "a": 2,
            "b": 3
        },
    }
    flattened = self.flatten(data)
    self.assertDictEqual(flattened, {"a": 1, "b/a": 2, "b/b": 3})

  def test_single_key_fn(self):
    data = {
        "a": 1,
        "b": 2,
    }
    flattened = self.flatten(data, key_fn=lambda path: "prefix_" + path[0])
    self.assertDictEqual(flattened, {
        "prefix_a": 1,
        "prefix_b": 2,
    })

  def test_single_key_fn_filtering(self):
    data = {
        "a": 1,
        "b": 2,
    }
    flattened = self.flatten(
        data,
        key_fn=lambda path: None if path[0] == "a" else "prefix_" + path[0])
    self.assertDictEqual(flattened, {
        "prefix_b": 2,
    })

  def test_single_nested_key_fn(self):
    data = {
        "a": 1,
        "b": {
            "a": 2,
            "b": 3
        },
    }
    with self.assertRaises(ValueError):
      # Fail on duplicate entries
      self.flatten(data, key_fn=lambda path: "prefix_" + path[0])

    flattened = self.flatten(
        data, key_fn=lambda path: "prefix_" + "/".join(path))
    self.assertDictEqual(flattened, {
        "prefix_a": 1,
        "prefix_b/a": 2,
        "prefix_b/b": 3,
    })

  def test_single_nested_key_fn_filtering(self):
    data = {
        "a": 1,
        "b": {
            "a": 2,
            "b": 3
        },
    }
    flattened = self.flatten(
        data,
        key_fn=lambda path: None
        if path[-1] == "a" else "prefix_" + "/".join(path))
    self.assertDictEqual(flattened, {
        "prefix_b/b": 3,
    })

  def test_multiple_flat(self):
    data_1 = {
        "a": 1,
        "b": 2,
    }
    with self.assertRaises(ValueError):
      # duplicate entries
      self.flatten(data_1, data_1)
    data_2 = {
        "c": 3,
        "d": 4,
    }
    flattened = self.flatten(data_1, data_2)
    self.assertDictEqual(flattened, {
        "a": 1,
        "b": 2,
        "c": 3,
        "d": 4,
    })


class V8CheckoutFinderTestCase(BaseCrossbenchTestCase):

  def test_find_none(self):
    self.assertIsNone(helper.V8CheckoutFinder(self.platform).v8_checkout)

  def _add_v8_checkout_files(self, checkout_dir: pathlib.Path) -> None:
    self.assertIsNone(helper.V8CheckoutFinder(self.platform).v8_checkout)
    (checkout_dir / ".git").mkdir(parents=True)
    self.assertIsNone(helper.V8CheckoutFinder(self.platform).v8_checkout)
    self.fs.create_file(checkout_dir / "include" / "v8.h", st_size=100)

  def test_D8_PATH(self):
    with mock.patch.dict(os.environ, {}, clear=True):
      self.assertIsNone(helper.V8CheckoutFinder(self.platform).v8_checkout)
    candidate_dir = pathlib.Path("/custom/v8/")
    d8_path = candidate_dir / "out/x64.release/d8"
    with mock.patch.dict(os.environ, {"D8_PATH": str(d8_path)}, clear=True):
      self.assertIsNone(helper.V8CheckoutFinder(self.platform).v8_checkout)
    self._add_v8_checkout_files(candidate_dir)
    with mock.patch.dict(os.environ, {"D8_PATH": str(d8_path)}, clear=True):
      self.assertEqual(
          helper.V8CheckoutFinder(self.platform).v8_checkout, candidate_dir)
    # Still NONE without custom D8_PATH env var.
    self.assertIsNone(helper.V8CheckoutFinder(self.platform).v8_checkout)

  def test_known_location(self):
    checkout_dir = pathlib.Path.home() / "v8/v8"
    self.assertIsNone(helper.V8CheckoutFinder(self.platform).v8_checkout)
    checkout_dir.mkdir(parents=True)
    self._add_v8_checkout_files(checkout_dir)
    self.assertEqual(
        helper.V8CheckoutFinder(self.platform).v8_checkout, checkout_dir)

  def test_module_relative(self):
    self.assertIsNone(helper.V8CheckoutFinder(self.platform).v8_checkout)
    path = pathlib.Path(__file__)
    self.assertFalse(path.exists())
    if "google3" in path.parts:
      fake_chrome_root = path.parents[5]
    else:
      fake_chrome_root = path.parents[4]
    checkout_dir = fake_chrome_root / "v8"
    self.assertIsNone(helper.V8CheckoutFinder(self.platform).v8_checkout)
    self._add_v8_checkout_files(checkout_dir)
    self.assertEqual(
        helper.V8CheckoutFinder(self.platform).v8_checkout, checkout_dir)


if __name__ == "__main__":
  sys.exit(pytest.main([__file__]))
