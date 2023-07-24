# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt
import unittest

from crossbench.cli_helper import (Duration, parse_httpx_url_str,
                                   parse_non_empty_str, parse_positive_int,
                                   parse_positive_zero_int,
                                   parse_positive_zero_float)


class DurationTestCase(unittest.TestCase):

  def test_parse_negative(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      Duration.parse(-1)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      Duration.parse("-1")
    self.assertIn("-1", str(cm.exception))

  def test_parse_empty(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      Duration.parse("")

  def test_no_unit(self):
    self.assertEqual(Duration.parse("200"), dt.timedelta(seconds=200))
    self.assertEqual(Duration.parse(200), dt.timedelta(seconds=200))

  def test_milliseconds(self):
    self.assertEqual(Duration.parse("27.5ms"), dt.timedelta(milliseconds=27.5))
    self.assertEqual(
        Duration.parse("27.5 millis"), dt.timedelta(milliseconds=27.5))
    self.assertEqual(
        Duration.parse("27.5 milliseconds"), dt.timedelta(milliseconds=27.5))

  def test_seconds(self):
    self.assertEqual(Duration.parse("27.5s"), dt.timedelta(seconds=27.5))
    self.assertEqual(Duration.parse("1 sec"), dt.timedelta(seconds=1))
    self.assertEqual(Duration.parse("27.5 secs"), dt.timedelta(seconds=27.5))
    self.assertEqual(Duration.parse("1 second"), dt.timedelta(seconds=1))
    self.assertEqual(Duration.parse("27.5 seconds"), dt.timedelta(seconds=27.5))

  def test_minutes(self):
    self.assertEqual(Duration.parse("27.5m"), dt.timedelta(minutes=27.5))
    self.assertEqual(Duration.parse("1 min"), dt.timedelta(minutes=1))
    self.assertEqual(Duration.parse("27.5 mins"), dt.timedelta(minutes=27.5))
    self.assertEqual(Duration.parse("1 minute"), dt.timedelta(minutes=1))
    self.assertEqual(Duration.parse("27.5 minutes"), dt.timedelta(minutes=27.5))

  def test_hours(self):
    self.assertEqual(Duration.parse("27.5h"), dt.timedelta(hours=27.5))
    self.assertEqual(Duration.parse("0.1 h"), dt.timedelta(hours=0.1))
    self.assertEqual(Duration.parse("27.5 hrs"), dt.timedelta(hours=27.5))
    self.assertEqual(Duration.parse("1 hour"), dt.timedelta(hours=1))
    self.assertEqual(Duration.parse("27.5 hours"), dt.timedelta(hours=27.5))


class ArgParserHelperTestCase(unittest.TestCase):

  def test_parse_non_empty_str(self):
    self.assertEqual(parse_non_empty_str("a string"), "a string")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      parse_non_empty_str("")
    self.assertIn("empty", str(cm.exception))

  def test_parse_httpx_url_str(self):
    for valid in ("http://foo.com", "https://foo.com", "http://localhost:800"):
      self.assertEqual(parse_httpx_url_str(valid), valid)
    for invalid in ("", "ftp://localhost:32", "http://///"):
      with self.assertRaises(argparse.ArgumentTypeError) as cm:
        _ = parse_httpx_url_str(invalid)
      self.assertIn(invalid, str(cm.exception))

  def test_parse_positive_int(self):
    self.assertEqual(parse_positive_int("1"), 1)
    self.assertEqual(parse_positive_int("123"), 123)
    for invalid in ("", "0", "-1", "-1.2", "1.2", "Nan", "inf", "-inf",
                    "invalid"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _ = parse_positive_int(invalid)

  def test_parse_positive_zero_int(self):
    self.assertEqual(parse_positive_zero_int("1"), 1)
    self.assertEqual(parse_positive_zero_int("0"), 0)
    for invalid in ("", "-1", "-1.2", "1.2", "NaN", "inf", "-inf", "invalid"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _ = parse_positive_zero_int(invalid)

  def test_parse_positive_zero_float(self):
    self.assertEqual(parse_positive_zero_float("1"), 1)
    self.assertEqual(parse_positive_zero_float("0"), 0)
    self.assertEqual(parse_positive_zero_float("0.0"), 0)
    self.assertEqual(parse_positive_zero_float("1.23"), 1.23)
    for invalid in ("", "-1", "-1.2", "NaN", "inf", "-inf", "invalid"):
      with self.assertRaises(argparse.ArgumentTypeError):
        _ = parse_positive_zero_float(invalid)
