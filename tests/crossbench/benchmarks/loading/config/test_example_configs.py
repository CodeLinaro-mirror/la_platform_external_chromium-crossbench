# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest

import hjson

from crossbench.benchmarks.loading.config.pages import PagesConfig
from crossbench.helper import ChangeCWD
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


class TestExamplePageConfig(CrossbenchFakeFsTestCase):

  CNN_JS_INSTRUMENTATION_PATH = (
      test_helper.config_dir() / "benchmark/loadline/cnn_instrumentation.js")

  GLOBO_JS_INSTRUMENTATION_PATH = (
      test_helper.config_dir() / "benchmark/loadline/globo_instrumentation.js")

  YT_JS_INSTRUMENTATION_PATH = (
      test_helper.config_dir() / "benchmark/loadline/youtube_instrumentation.js")

  def test_parse_example_page_config_file(self):
    example_config_file = test_helper.config_dir() / "doc/page.config.hjson"
    self.fs.add_real_file(example_config_file)
    file_config = PagesConfig.parse(example_config_file)
    with example_config_file.open(encoding="utf-8") as f:
      data = hjson.load(f)
    dict_config = PagesConfig.parse_dict(data)
    self.assertTrue(dict_config.pages)
    self.assertTrue(file_config.pages)
    for page in dict_config.pages:
      self.assertEqual(len(page.blocks), 1)
      self.assertGreater(len(page.blocks[0].actions), 1)

  def test_parse_android_page_config_file(self):
    example_config_file = (
        test_helper.config_dir() / "team/woa/android_input_page_config.hjson")
    self.fs.add_real_file(example_config_file)
    file_config = PagesConfig.parse(example_config_file)
    with example_config_file.open(encoding="utf-8") as f:
      data = hjson.load(f)
    dict_config = PagesConfig.parse_dict(data)
    self.assertTrue(dict_config.pages)
    self.assertTrue(file_config.pages)
    for page in dict_config.pages:
      self.assertEqual(len(page.blocks), 1)
      self.assertGreater(len(page.blocks[0].actions), 1)

  def test_parse_loadline_page_config_phone(self):
    self.fs.add_real_file(self.CNN_JS_INSTRUMENTATION_PATH)
    self.fs.add_real_file(self.GLOBO_JS_INSTRUMENTATION_PATH)

    config_file = (
        test_helper.config_dir() / "benchmark/loadline/page_config_phone.hjson")
    self.fs.add_real_file(config_file)
    file_config = PagesConfig.parse(config_file)
    with config_file.open(encoding="utf-8") as f:
      data = hjson.load(f)
    with ChangeCWD(test_helper.config_dir() / "benchmark/loadline"):
      dict_config = PagesConfig.parse_dict(data)
    self.assertTrue(dict_config.pages)
    self.assertTrue(file_config.pages)
    for page in dict_config.pages:
      self.assertEqual(len(page.blocks), 1)
      self.assertGreater(len(page.blocks[0].actions), 1)

  def test_parse_loadline_page_config_tablet(self):
    self.fs.add_real_file(self.CNN_JS_INSTRUMENTATION_PATH)
    self.fs.add_real_file(self.YT_JS_INSTRUMENTATION_PATH)

    config_file = (
        test_helper.config_dir() / "benchmark/loadline/page_config_tablet.hjson")
    self.fs.add_real_file(config_file)
    file_config = PagesConfig.parse(config_file)
    with config_file.open(encoding="utf-8") as f:
      data = hjson.load(f)
    with ChangeCWD(test_helper.config_dir() / "benchmark/loadline"):
      dict_config = PagesConfig.parse_dict(data)
    self.assertTrue(dict_config.pages)
    self.assertTrue(file_config.pages)
    for page in dict_config.pages:
      self.assertEqual(len(page.blocks), 1)
      self.assertGreater(len(page.blocks[0].actions), 1)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
