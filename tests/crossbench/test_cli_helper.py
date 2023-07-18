# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations
import unittest
import argparse

from crossbench.cli_helper import Duration


class DurationTestCase(unittest.TestCase):

  def test_parse_negative(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      Duration.parse(-1)
    with self.assertRaises(argparse.ArgumentTypeError):
      Duration.parse("-1")

  def test_parse_empty(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      Duration.parse("")

  def test_no_unit(self):
    # TODO: switch over to dt.timedelta for consistency
    d = Duration.parse("200")
    self.assertEqual(d, 200)
    d = Duration.parse(200)
    self.assertEqual(d, 200)
