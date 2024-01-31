# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import unittest

import hjson

from crossbench.benchmarks.loading.page_config import PageConfig
from tests import test_helper


class TestExamplePageConfig(unittest.TestCase):

  @unittest.skipIf(hjson.__name__ != "hjson", "hjson not available")
  def test_parse_example_page_config_file(self):
    for config_file_name in [
      'browsing_story.hjson',
      'meet_story.hjson',
      'netflix_story.hjson'
    ]:
      config_file = pathlib.Path(
          __file__).parents[3] / "crossbench" / "benchmarks" \
            / "experimental" / "power" / config_file_name
      with config_file.open(encoding="utf-8") as f:
        file_config = PageConfig()
        file_config.load(f)
      with config_file.open(encoding="utf-8") as f:
        data = hjson.load(f)
      dict_config = PageConfig()
      dict_config.load_dict(data)
      self.assertTrue(dict_config.stories)
      self.assertTrue(file_config.stories)
      for story in dict_config.stories:
        json_data = story.details_json()
        self.assertIn("actions", json_data)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
