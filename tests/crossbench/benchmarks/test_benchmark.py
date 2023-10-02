# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
import datetime as dt

from crossbench.benchmarks.benchmark import PressBenchmarkStoryFilter
from crossbench.runner.run import Run
from crossbench.stories.press_benchmark import PressBenchmarkStory


class TestingStory(PressBenchmarkStory):
  NAME = "TestingStory"
  URL = "http://test.com"
  SUBSTORIES = (
      "Story-1",
      "Story-2",
      "Story-3",
      "Story-4",
  )

  @property
  def substory_duration(self) -> dt.timedelta:
    return dt.timedelta(seconds=0.1)

  def run(self, run: Run) -> None:
    pass


class PressBenchmarkStoryFilterTestCase(unittest.TestCase):

  def test_empty(self):
    with self.assertRaises(ValueError):
      _ = PressBenchmarkStoryFilter(TestingStory, [])

  def test_all(self):
    stories = PressBenchmarkStoryFilter(TestingStory, ["all"]).stories
    self.assertEqual(len(stories), 1)
    story: TestingStory = stories[0]
    self.assertSequenceEqual(story.substories, TestingStory.SUBSTORIES)

  def test_all_separate(self):
    stories = PressBenchmarkStoryFilter(
        TestingStory, ["all"], separate=True).stories
    self.assertSequenceEqual([story.substories[0] for story in stories],
                             TestingStory.SUBSTORIES)
    for story in stories:
      self.assertTrue(len(story.substories), 1)

  def test_match_regexp_none(self):
    with self.assertRaises(ValueError) as cm:
      _ = PressBenchmarkStoryFilter(TestingStory, ["Story"]).stories
    self.assertIn("Story", str(cm.exception))

  def test_match_regexp_some(self):
    stories = PressBenchmarkStoryFilter(TestingStory, [".*-3"]).stories
    self.assertEqual(len(stories), 1)
    story: TestingStory = stories[0]
    self.assertSequenceEqual(story.substories, ["Story-3"])

  def test_match_regexp_all(self):
    stories = PressBenchmarkStoryFilter(TestingStory, ["Story.*"]).stories
    self.assertEqual(len(stories), 1)
    story: TestingStory = stories[0]
    self.assertSequenceEqual(story.substories, TestingStory.SUBSTORIES)

  def test_match_regexp_all_wrong_case(self):
    stories = PressBenchmarkStoryFilter(TestingStory, ["StOrY.*"]).stories
    self.assertEqual(len(stories), 1)
    story: TestingStory = stories[0]
    self.assertSequenceEqual(story.substories, TestingStory.SUBSTORIES)
