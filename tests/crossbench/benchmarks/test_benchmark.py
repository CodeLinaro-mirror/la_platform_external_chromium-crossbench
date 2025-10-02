# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import datetime as dt
import unittest
from typing import TYPE_CHECKING

from typing_extensions import override

from crossbench.benchmarks.base import PressBenchmarkStoryFilter, RegexFilter
from crossbench.stories.press_benchmark import PressBenchmarkStory
from tests import test_helper

if TYPE_CHECKING:
  from crossbench.runner.run import Run


class MockStory(PressBenchmarkStory):
  NAME = "MockStory"
  URL = "http://test.com"
  SUBSTORIES = (
      "Story-1",
      "Story-2",
      "Story-3",
      "Story-4",
  )

  @property
  @override
  def substory_duration(self) -> dt.timedelta:
    return dt.timedelta(seconds=0.1)

  def run(self, run: Run) -> None:
    pass


class PressBenchmarkStoryFilterTestCase(unittest.TestCase):

  def test_empty(self):
    with self.assertRaises(ValueError):
      _ = PressBenchmarkStoryFilter(MockStory, [])

  def test_all(self):
    stories = PressBenchmarkStoryFilter(MockStory, ["all"]).stories
    self.assertEqual(len(stories), 1)
    story: MockStory = stories[0]
    self.assertSequenceEqual(story.substories, MockStory.SUBSTORIES)

  def test_all_separate(self):
    stories = PressBenchmarkStoryFilter(
        MockStory, ["all"], separate=True).stories
    self.assertSequenceEqual([story.substories[0] for story in stories],
                             MockStory.SUBSTORIES)
    for story in stories:
      self.assertTrue(len(story.substories), 1)

  def test_match_regexp_none(self):
    with self.assertRaises(ValueError) as cm:
      _ = PressBenchmarkStoryFilter(MockStory, ["Story"]).stories
    self.assertIn("Story", str(cm.exception))

  def test_match_regexp_some(self):
    stories = PressBenchmarkStoryFilter(MockStory, [".*-3"]).stories
    self.assertEqual(len(stories), 1)
    story: MockStory = stories[0]
    self.assertSequenceEqual(story.substories, ["Story-3"])

  def test_match_regexp_all(self):
    stories = PressBenchmarkStoryFilter(MockStory, ["Story.*"]).stories
    self.assertEqual(len(stories), 1)
    story: MockStory = stories[0]
    self.assertSequenceEqual(story.substories, MockStory.SUBSTORIES)

  def test_match_regexp_all_wrong_case(self):
    stories = PressBenchmarkStoryFilter(MockStory, ["StOrY.*"]).stories
    self.assertEqual(len(stories), 1)
    story: MockStory = stories[0]
    self.assertSequenceEqual(story.substories, MockStory.SUBSTORIES)


class RegexFilterTestCase(unittest.TestCase):

  def test_all(self):
    regex_filter = RegexFilter(["story1", "story2"], ["story1"])
    selected = regex_filter.process_all(["all"])
    self.assertSequenceEqual(selected, ["story1", "story2"])

  def test_default(self):
    regex_filter = RegexFilter(["story1", "story2"], ["story1"])
    selected = regex_filter.process_all(["default"])
    self.assertSequenceEqual(selected, ["story1"])

  def test_match_regexp_none(self):
    regex_filter = RegexFilter(["story1", "story2"], ["story1"])
    with self.assertRaises(ValueError) as cm:
      regex_filter.process_all(["no_such_story"])
    self.assertIn("no_such_story", str(cm.exception))

  def test_match_regexp_some(self):
    regex_filter = RegexFilter(["story1", "story2"], ["story1"])
    selected = regex_filter.process_all([".*2"])
    self.assertSequenceEqual(selected, ["story2"])

  def test_match_regexp_all(self):
    regex_filter = RegexFilter(["story1", "story2"], ["story1"])
    selected = regex_filter.process_all(["story.*"])
    self.assertSequenceEqual(selected, ["story1", "story2"])

  def test_match_regexp_all_wrong_case(self):
    regex_filter = RegexFilter(["story1", "story2"], ["story1"])
    selected = regex_filter.process_all(["StOrY.*"])
    self.assertSequenceEqual(selected, ["story1", "story2"])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
