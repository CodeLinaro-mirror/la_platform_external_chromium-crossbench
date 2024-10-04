# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import unittest
from typing import Any
from urllib import parse as urlparse

from crossbench.parse import (DurationParser, NumberParser, ObjectParser,
                              PathParser)
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


class DurationParserTestCase(unittest.TestCase):

  def test_parse_negative(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      DurationParser.positive_duration(-1)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      DurationParser.positive_duration("-1")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      DurationParser.positive_or_zero_duration("-1")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      DurationParser.positive_or_zero_duration(dt.timedelta(seconds=-1))
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      DurationParser.positive_duration("-1")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      DurationParser.positive_duration(dt.timedelta(seconds=-1))
    self.assertIn("-1", str(cm.exception))
    self.assertEqual(DurationParser.any_duration("-1.5").total_seconds(), -1.5)

  def test_parse_zero(self):
    self.assertEqual(DurationParser.any_duration("0").total_seconds(), 0)
    self.assertEqual(DurationParser.any_duration("0s").total_seconds(), 0)
    self.assertEqual(DurationParser.any_duration("0.0").total_seconds(), 0)
    self.assertEqual(
        DurationParser.positive_or_zero_duration("0.0").total_seconds(), 0)
    for invalid in (-1, 0, "-1", "0", "invalid", dt.timedelta(0),
                    dt.timedelta(seconds=-1)):
      with self.assertRaises(argparse.ArgumentTypeError) as cm:
        DurationParser.positive_duration(invalid)
      self.assertIn(str(invalid), str(cm.exception))
      with self.assertRaises(argparse.ArgumentTypeError) as cm:
        DurationParser.positive_duration(invalid)
      self.assertIn(str(invalid), str(cm.exception))

  def test_parse_empty(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      DurationParser.positive_duration("")
    with self.assertRaises(argparse.ArgumentTypeError):
      DurationParser.any_duration("")
    with self.assertRaises(argparse.ArgumentTypeError):
      DurationParser.positive_or_zero_duration("")
    with self.assertRaises(argparse.ArgumentTypeError):
      DurationParser.positive_duration("")

  def test_invalid_suffix(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      DurationParser.positive_duration("100XXX")
    self.assertIn("Unknown duration format", str(cm.exception))
    with self.assertRaises(argparse.ArgumentTypeError):
      DurationParser.positive_duration("X0XX")
    with self.assertRaises(argparse.ArgumentTypeError):
      DurationParser.positive_duration("100X0XX")

  def test_no_unit(self):
    self.assertEqual(
        DurationParser.positive_duration("200"), dt.timedelta(seconds=200))
    self.assertEqual(
        DurationParser.positive_duration(200), dt.timedelta(seconds=200))

  def test_milliseconds(self):
    self.assertEqual(
        DurationParser.positive_duration("27.5ms"),
        dt.timedelta(milliseconds=27.5))
    self.assertEqual(
        DurationParser.positive_duration(dt.timedelta(milliseconds=27.5)),
        dt.timedelta(milliseconds=27.5))
    self.assertEqual(
        DurationParser.positive_duration("27.5 millis"),
        dt.timedelta(milliseconds=27.5))
    self.assertEqual(
        DurationParser.positive_duration("27.5 milliseconds"),
        dt.timedelta(milliseconds=27.5))

  def test_seconds(self):
    self.assertEqual(
        DurationParser.positive_duration("27.5s"), dt.timedelta(seconds=27.5))
    self.assertEqual(
        DurationParser.positive_duration("1 sec"), dt.timedelta(seconds=1))
    self.assertEqual(
        DurationParser.positive_duration("27.5 secs"),
        dt.timedelta(seconds=27.5))
    self.assertEqual(
        DurationParser.positive_duration("1 second"), dt.timedelta(seconds=1))
    self.assertEqual(
        DurationParser.positive_duration("27.5 seconds"),
        dt.timedelta(seconds=27.5))

  def test_minutes(self):
    self.assertEqual(
        DurationParser.positive_duration("27.5m"), dt.timedelta(minutes=27.5))
    self.assertEqual(
        DurationParser.positive_duration("1 min"), dt.timedelta(minutes=1))
    self.assertEqual(
        DurationParser.positive_duration("27.5 mins"),
        dt.timedelta(minutes=27.5))
    self.assertEqual(
        DurationParser.positive_duration("1 minute"), dt.timedelta(minutes=1))
    self.assertEqual(
        DurationParser.positive_duration("27.5 minutes"),
        dt.timedelta(minutes=27.5))

  def test_hours(self):
    self.assertEqual(
        DurationParser.positive_duration("27.5h"), dt.timedelta(hours=27.5))
    self.assertEqual(
        DurationParser.positive_duration("0.1 h"), dt.timedelta(hours=0.1))
    self.assertEqual(
        DurationParser.positive_duration("27.5 hrs"), dt.timedelta(hours=27.5))
    self.assertEqual(
        DurationParser.positive_duration("1 hour"), dt.timedelta(hours=1))
    self.assertEqual(
        DurationParser.positive_duration("27.5 hours"),
        dt.timedelta(hours=27.5))


class ObjectParserHelperTestCase(CrossbenchFakeFsTestCase):

  def setUp(self):
    super().setUp()
    self._json_test_data = {"int": 1, "array": [1, "2"]}

  def test_parse_any_str(self):
    self.assertEqual(ObjectParser.any_str(""), "")
    self.assertEqual(ObjectParser.any_str("1234"), "1234")

  def test_parse_any_str_invalid(self):
    for invalid in (None, 1, [], {}, [1], ["a"], {"a": "a"}):
      with self.assertRaises(argparse.ArgumentTypeError) as cm:
        ObjectParser.any_str(invalid)
      self.assertIn(str(invalid), str(cm.exception))

  def test_parse_non_empty_str(self):
    self.assertEqual(ObjectParser.non_empty_str("a string"), "a string")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      ObjectParser.non_empty_str("")
    self.assertIn("empty", str(cm.exception))

  def test_parse_httpx_url_str(self):
    for valid in ("http://foo.com", "https://foo.com", "http://localhost:800"):
      self.assertEqual(ObjectParser.httpx_url_str(valid), valid)
    for invalid in ("", "ftp://localhost:32", "http://///"):
      with self.assertRaises(argparse.ArgumentTypeError) as cm:
        _ = ObjectParser.httpx_url_str(invalid)
      self.assertIn(invalid, str(cm.exception))

  def test_parse_any_int(self):
    self.assertEqual(NumberParser.any_int("-123456"), -123456)
    self.assertEqual(NumberParser.any_int(-123456), -123456)
    self.assertEqual(NumberParser.any_int("-1"), -1)
    self.assertEqual(NumberParser.any_int(-1), -1)
    self.assertEqual(NumberParser.any_int("0"), 0)
    self.assertEqual(NumberParser.any_int(0), 0)
    self.assertEqual(NumberParser.any_int("1"), 1)
    self.assertEqual(NumberParser.any_int(1), 1)
    self.assertEqual(NumberParser.any_int("123456"), 123456)
    self.assertEqual(NumberParser.any_int(123456), 123456)

  def test_parse_any_int_invalid(self):
    for invalid in ("", "-1.2", "1.2", "100.001", "Nan", "inf", "-inf",
                    "invalid"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _ = NumberParser.any_int(invalid)

  def test_parse_positive_int(self):
    self.assertEqual(NumberParser.positive_int("1"), 1)
    self.assertEqual(NumberParser.positive_int("123"), 123)

  def test_parse_positive_int_ivalid(self):
    for invalid in ("", "0", "-1", "-1.2", "1.2", "Nan", "inf", "-inf",
                    "invalid"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _ = NumberParser.positive_int(invalid)

  def test_parse_positive_zero_int(self):
    self.assertEqual(NumberParser.positive_zero_int("1"), 1)
    self.assertEqual(NumberParser.positive_zero_int("0"), 0)

  def test_parse_positive_zero_int_invalid(self):
    for invalid in ("", "-1", "-1.2", "1.2", "NaN", "inf", "-inf", "invalid"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _ = NumberParser.positive_zero_int(invalid)

  def test_parse_any_float(self):
    self.assertEqual(NumberParser.any_float("-1.2"), -1.2)
    self.assertEqual(NumberParser.any_float(-1.2), -1.2)
    self.assertEqual(NumberParser.any_float("-1"), -1.0)
    self.assertEqual(NumberParser.any_float(-1), -1.0)
    self.assertEqual(NumberParser.any_float("0"), 0.0)
    self.assertEqual(NumberParser.any_float(0), 0.0)
    self.assertEqual(NumberParser.any_float("0.0"), 0.0)
    self.assertEqual(NumberParser.any_float(0.0), 0.0)
    self.assertEqual(NumberParser.any_float("0.1"), 0.1)
    self.assertEqual(NumberParser.any_float(0.1), 0.1)

  def test_parse_float_invalid(self):
    for invalid in ("", "abc", "NaN", "inf", "-inf", "invalid"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _ = NumberParser.positive_zero_float(invalid)

  def test_parse_positive_zero_float(self):
    self.assertEqual(NumberParser.positive_zero_float("1"), 1.0)
    self.assertEqual(NumberParser.positive_zero_float("0"), 0.0)
    self.assertEqual(NumberParser.positive_zero_float("0.0"), 0.0)
    self.assertEqual(NumberParser.positive_zero_float("1.23"), 1.23)

  def test_parse_positive_zero_float_invlid(self):
    for invalid in ("", "-1", "-1.2", "NaN", "inf", "-inf", "invalid"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _ = NumberParser.positive_zero_float(invalid)

  def test_parse_port_number(self):
    self.assertEqual(NumberParser.port_number(1), 1)
    self.assertEqual(NumberParser.port_number("1"), 1)
    self.assertEqual(NumberParser.port_number(440), 440)
    self.assertEqual(NumberParser.port_number("440"), 440)
    self.assertEqual(NumberParser.port_number(65535), 65535)
    self.assertEqual(NumberParser.port_number("65535"), 65535)

  def test_parse_port_number_invalid(self):
    for invalid in ("", "-1", "-1.2", "6553500", "inf", "-inf", "invalid"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _ = NumberParser.port_number(invalid)

  def _json_file_test_helper(self, parser) -> Any:
    with self.assertRaises(argparse.ArgumentTypeError):
      parser("file")

    path = pathlib.Path("file.json")
    self.assertFalse(path.exists())
    with self.assertRaises(argparse.ArgumentTypeError):
      parser(path)

    path.touch()
    with self.assertRaises(argparse.ArgumentTypeError):
      parser(path)

    with path.open("w", encoding="utf-8") as f:
      f.write("{invalid json data")
    with self.assertRaises(argparse.ArgumentTypeError):
      parser(path)
    # Test very long lines too.
    with path.open("w", encoding="utf-8") as f:
      f.write("{\n invalid json data" + "." * 100)
    with self.assertRaises(argparse.ArgumentTypeError):
      parser(path)

    with path.open("w", encoding="utf-8") as f:
      f.write("""{
              'a': {},
              'c': }}
              """)
    with self.assertRaises(argparse.ArgumentTypeError):
      parser(path)

    with path.open("w", encoding="utf-8") as f:
      json.dump(self._json_test_data, f)
    str_result = parser(str(path))
    path_result = parser(path)
    self.assertEqual(str_result, path_result)
    return str_result

  def test_parse_json_file(self):
    result = self._json_file_test_helper(ObjectParser.json_file)
    self.assertDictEqual(self._json_test_data, result)

  def test_parse_json_file_path(self):
    result = self._json_file_test_helper(PathParser.json_file_path)
    self.assertEqual(pathlib.Path("file.json"), result)

  def test_parse_hjson_file_path(self):
    result = self._json_file_test_helper(PathParser.hjson_file_path)
    self.assertEqual(pathlib.Path("file.json"), result)

  def test_parse_inline_hjson(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      ObjectParser.inline_hjson("")
    with self.assertRaises(argparse.ArgumentTypeError):
      ObjectParser.inline_hjson("{invalid json}")
    with self.assertRaises(argparse.ArgumentTypeError):
      ObjectParser.inline_hjson("{'asdfas':'asdf}")
    self.assertDictEqual(
        self._json_test_data,
        ObjectParser.inline_hjson(json.dumps(self._json_test_data)))

  def test_parse_dir_path(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      PathParser.dir_path("")
    file = pathlib.Path("file")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      PathParser.dir_path(file)
    self.assertIn("does not exist", str(cm.exception))
    file.touch()
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      PathParser.dir_path(file)
    self.assertIn("not a folder", str(cm.exception))
    folder = pathlib.Path("folder")
    folder.mkdir()
    self.assertEqual(folder, PathParser.dir_path(folder))
    self.assertEqual(folder, PathParser.dir_path(str(folder)))

  def test_parse_non_empty_dir_path(self):
    folder = pathlib.Path("folder")
    folder.mkdir()
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      PathParser.non_empty_dir_path(folder)
    self.assertIn("empty", str(cm.exception))
    (folder / "foo").touch()
    self.assertEqual(folder, PathParser.non_empty_dir_path(folder))
    self.assertEqual(folder, PathParser.non_empty_dir_path(str(folder)))

  def test_parse_non_empty_file_path(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      PathParser.non_empty_file_path("")
    folder = pathlib.Path("folder")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      PathParser.non_empty_file_path(folder)
    self.assertIn("does not exist", str(cm.exception))
    folder.mkdir()
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      PathParser.non_empty_file_path(folder)
    self.assertIn("not a file", str(cm.exception))
    file = pathlib.Path("file")
    file.touch()
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      self.assertEqual(file, PathParser.non_empty_file_path(file))
    self.assertIn("is an empty file", str(cm.exception))

    with file.open("w") as f:
      f.write("fooo")
    self.assertEqual(file, PathParser.non_empty_file_path(file))

  def test_parse_existing_file_path(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      PathParser.existing_file_path("")
    folder = pathlib.Path("folder")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      PathParser.existing_file_path(folder)
    self.assertIn("does not exist", str(cm.exception))
    folder.mkdir()
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      PathParser.existing_file_path(folder)
    self.assertIn("not a file", str(cm.exception))
    file = pathlib.Path("file")
    file.touch()
    self.assertEqual(file, PathParser.existing_file_path(file))

  def test_parse_path(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      PathParser.path("")
    folder = pathlib.Path("folder")
    folder.mkdir()
    self.assertEqual(folder, PathParser.path(folder))
    file = pathlib.Path("file")
    file.touch()
    self.assertEqual(file, PathParser.path(file))

  def test_parse_bool_success(self):
    self.assertIs(ObjectParser.bool("true"), True)
    self.assertIs(ObjectParser.bool("True"), True)
    self.assertIs(ObjectParser.bool(True), True)
    self.assertIs(ObjectParser.bool("false"), False)
    self.assertIs(ObjectParser.bool("False"), False)
    self.assertIs(ObjectParser.bool(False), False)

  def test_parse_bool_invalid(self):
    for invalid in (1, 0, "1", "0", "", None, [], tuple()):
      with self.assertRaises(argparse.ArgumentTypeError):
        ObjectParser.bool(invalid)

  def test_parse_sh_cmd(self):
    self.assertListEqual(ObjectParser.sh_cmd("ls -al ."), ["ls", "-al", "."])
    self.assertListEqual(ObjectParser.sh_cmd("ls -al '.'"), ["ls", "-al", "."])
    self.assertListEqual(
        ObjectParser.sh_cmd(";ls -al '.'"), [";ls", "-al", "."])
    self.assertListEqual(
        ObjectParser.sh_cmd(("ls", "-al", ".")), ["ls", "-al", "."])

  def test_parse_sh_cmd_invalid(self):
    for invalid in (1, "", None, [], "ls -al \"."):
      with self.assertRaises(argparse.ArgumentTypeError):
        ObjectParser.sh_cmd(invalid)

  def test_parse_dict_invalid(self):
    for invalid in (1, 0, "1", "0", "", None, [], tuple()):
      with self.assertRaises(argparse.ArgumentTypeError):
        ObjectParser.dict(invalid)

  def test_parse_dict(self):
    self.assertDictEqual(ObjectParser.dict({}), {})
    self.assertDictEqual(ObjectParser.dict({"A": 2}), {"A": 2})

  def test_parse_non_empty_dict_invalid(self):
    for invalid in (1, 0, "1", "0", "", None, [], tuple(), dict()):
      with self.assertRaises(argparse.ArgumentTypeError):
        ObjectParser.non_empty_dict(invalid)

  def test_parse_non_empty_dict(self):
    result = ObjectParser.non_empty_dict({"a": 1})
    self.assertDictEqual(result, {"a": 1})

  def test_parse_unique_sequence(self):
    self.assertListEqual(ObjectParser.unique_sequence([]), [])
    self.assertTupleEqual(ObjectParser.unique_sequence(tuple()), tuple())
    self.assertListEqual(ObjectParser.unique_sequence([1, 2, 3]), [1, 2, 3])
    self.assertTupleEqual(ObjectParser.unique_sequence((1, 2, 3)), (1, 2, 3))

  def test_parse_unique_sequence_invalid(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      ObjectParser.unique_sequence([1, 1, 2, 2, 2, 3, 5, 5])
    self.assertIn("duplicates", str(cm.exception))
    self.assertIn("1, 2, 5", str(cm.exception))

  def test_parse_unique_sequence_custom_exception(self):

    class CustomException(Exception):
      pass

    with self.assertRaises(CustomException):
      ObjectParser.unique_sequence([1, 1], error_cls=CustomException)

  def test_parse_unique_sequence_custom_name(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      ObjectParser.unique_sequence([1, 1], name="custom test name")
    self.assertIn("custom test name", str(cm.exception))

  def test_parse_sequence(self):
    self.assertListEqual(ObjectParser.sequence([]), [])
    self.assertListEqual(ObjectParser.sequence([1, 2]), [1, 2])
    self.assertTupleEqual(ObjectParser.sequence(tuple()), tuple())
    self.assertTupleEqual(ObjectParser.sequence((1, 2)), (1, 2))

  def test_parse_sequence_invalid(self):
    for invalid in ("", "1", 1, {}, {"a": 1}, set(), set((1, 2))):
      with self.subTest(invalid=invalid):
        with self.assertRaises(argparse.ArgumentTypeError):
          ObjectParser.sequence(invalid)

  def test_parse_non_empty_sequence(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = ObjectParser.non_empty_sequence([])
    self.assertListEqual(ObjectParser.non_empty_sequence([1, 2]), [1, 2])
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = ObjectParser.non_empty_sequence(tuple())
    self.assertTupleEqual(ObjectParser.non_empty_sequence((1, 2)), (1, 2))

  def test_parse_non_empty_sequence_invalid(self):
    for invalid in ("", "1", 1, {}, {"a": 1}, set(), set((1, 2)), (), []):
      with self.subTest(invalid=invalid):
        with self.assertRaises(argparse.ArgumentTypeError):
          ObjectParser.non_empty_sequence(invalid)

  def test_parse_fuzzy_url(self):
    expected = (
        ("/foo/bar", "file:///foo/bar"),
        ("C:/foo/bar", "file://C:/foo/bar"),
        ("1234.com", "https://1234.com"),
        ("http://1234.com", "http://1234.com"),
        ("test.com", "https://test.com"),
        ("test.com/", "https://test.com/"),
        ("test.com/1234", "https://test.com/1234"),
        ("test.com/bar", "https://test.com/bar"),
        ("test.com/bar?x=1", "https://test.com/bar?x=1"),
        ("test.com:1234", "https://test.com:1234"),
        ("test.com:1234/", "https://test.com:1234/"),
        ("test.com:1234/56", "https://test.com:1234/56"),
        ("test.com:1234/56/", "https://test.com:1234/56/"),
        ("test.com:1234/bar", "https://test.com:1234/bar"),
        ("test.com:1234/bar?x=1", "https://test.com:1234/bar?x=1"),
        ("localhost:8123", "https://localhost:8123"),
        ("localhost:8123/", "https://localhost:8123/"),
        ("localhost:8123/77", "https://localhost:8123/77"),
        ("localhost:8123/77/", "https://localhost:8123/77/"),
        ("localhost:8123/bar", "https://localhost:8123/bar"),
        ("localhost:8123/bar?x=1", "https://localhost:8123/bar?x=1"),
    )
    for url, result in expected:
      with self.subTest(url=url):
        self.assertEqual(ObjectParser.parse_fuzzy_url_str(url), result)
        parsed = ObjectParser.parse_fuzzy_url(url)
        self.assertEqual(urlparse.urlunparse(parsed), result)

  def test_parse_fuzzy_url_default_scheme(self):
    expected = ("test.com", "test.com/", "test.com/bar", "test.com/bar?x=1",
                "test.com:1234", "test.com:1234/", "test.com:1234/bar",
                "test.com:1234/bar?x=1", "localhost:8123", "localhost:8123/",
                "localhost:8123/bar", "localhost:8123/bar?x1")
    for url in expected:
      with self.subTest(url=url):
        result_default = f"https://{url}"
        self.assertEqual(ObjectParser.parse_fuzzy_url_str(url), result_default)
        parsed = ObjectParser.parse_fuzzy_url(url)
        self.assertEqual(urlparse.urlunparse(parsed), result_default)
        result_custom = f"ftp://{url}"
        self.assertEqual(
            ObjectParser.parse_fuzzy_url_str(url, default_scheme="ftp"),
            result_custom)
        parsed = ObjectParser.parse_fuzzy_url(url, default_scheme="ftp")
        self.assertEqual(urlparse.urlunparse(parsed), result_custom)

  def test_parse_url(self):
    expected = (
        ("file:///foo/bar", "file:///foo/bar"),
        ("about:blank", "about:blank"),
        ("http://test.com/bar", "http://test.com/bar"),
        ("https://test.com/bar", "https://test.com/bar"),
        ("http://test.com", "http://test.com"),
        ("https://test.com/", "https://test.com/"),
        ("http://test.com/bar", "http://test.com/bar"),
        ("https://test.com/bar?x=1", "https://test.com/bar?x=1"),
        ("http://test.com:1234", "http://test.com:1234"),
        ("https://test.com:1234/", "https://test.com:1234/"),
        ("http://test.com:1234/bar", "http://test.com:1234/bar"),
        ("https://test.com:1234/bar?x=1", "https://test.com:1234/bar?x=1"),
        ("http://localhost:8123", "http://localhost:8123"),
        ("https://localhost:8123/", "https://localhost:8123/"),
        ("http://localhost:8123/bar", "http://localhost:8123/bar"),
        ("https://localhost:8123/bar?x=1", "https://localhost:8123/bar?x=1"),
    )
    for url, result in expected:
      with self.subTest(url=url):
        self.assertEqual(ObjectParser.url_str(url), result)
        self.assertEqual(ObjectParser.parse_fuzzy_url_str(url), result)
        parsed = ObjectParser.url(url)
        self.assertEqual(urlparse.urlunparse(parsed), result)
        parsed_fuzzy = ObjectParser.parse_fuzzy_url(url)
        self.assertEqual(urlparse.urlunparse(parsed_fuzzy), result)

  def test_parse_url_invalid(self):
    for invalid in (None, "", {}, "http:// foo .com/bar", "htt p://foo.com",
                    "http://foo.com:-123/bar"):
      with self.subTest(invalid=invalid):
        with self.assertRaises(argparse.ArgumentTypeError):
          _ = ObjectParser.url(invalid)
        with self.assertRaises(argparse.ArgumentTypeError):
          _ = ObjectParser.url_str(invalid)
        with self.assertRaises(argparse.ArgumentTypeError):
          _ = ObjectParser.httpx_url_str(invalid)
        with self.assertRaises(argparse.ArgumentTypeError):
          _ = ObjectParser.parse_fuzzy_url_str(invalid)
        with self.assertRaises(argparse.ArgumentTypeError):
          _ = ObjectParser.parse_fuzzy_url(invalid)

  def test_parse_httpx_url_str_invalid(self):
    for invalid in ("ftp://foo.com:123/bar", "ssh://test.com"):
      with self.subTest(invalid=invalid):
        with self.assertRaises(argparse.ArgumentTypeError):
          _ = ObjectParser.httpx_url_str(invalid)

  def test_parse_url_scheme(self):
    url = "ftp://foo.com"
    parsed = ObjectParser.url(url)
    self.assertEqual(urlparse.urlunparse(parsed), url)
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = ObjectParser.url(url, schemes=("https",))
    parsed = ObjectParser.url(
        url, schemes=(
            "https",
            "ftp",
        ))
    self.assertEqual(urlparse.urlunparse(parsed), url)

  def test_parse_regexp(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      ObjectParser.regexp("\\")
    pattern = ObjectParser.regexp("^abc$")
    self.assertEqual(pattern.pattern, "^abc$")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
