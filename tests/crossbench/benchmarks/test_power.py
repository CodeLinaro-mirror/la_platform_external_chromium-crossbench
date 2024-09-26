# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import unittest

import hjson

from crossbench.benchmarks.loading.config.pages import PagesConfig
from tests import test_helper


class TestExamplePageConfig(unittest.TestCase):

  def test_parse_example_page_config_file(self):
    for config_file_name in [
      'browsing_story.hjson',
      'meet_story.hjson',
      'netflix_story.hjson'
    ]:
      config_file = test_helper.crossbench_dir() / "benchmarks" \
            / "experimental" / "power" / config_file_name
      file_config = PagesConfig.parse(config_file)
      with config_file.open(encoding="utf-8") as f:
        data = hjson.load(f)
      dict_config = PagesConfig.parse_dict(data)
      self.assertTrue(dict_config.pages)
      self.assertTrue(file_config.pages)
      for page in dict_config.pages:
        self.assertEqual(len(page.blocks), 1)
        self.assertTrue(page.blocks[0].actions)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
