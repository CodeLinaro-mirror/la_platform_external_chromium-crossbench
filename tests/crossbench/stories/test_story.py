# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import unittest

from crossbench.stories.story import Story
from tests import test_helper


class MockStory(Story):

  @classmethod
  def all_story_names(cls) -> tuple[str, ...]:
    return ("valid1", "valid2")

  def run(self, run) -> None:
    pass


class StoryTestCase(unittest.TestCase):

  def test_valid_names(self):
    story = MockStory("valid-name")
    self.assertEqual(story.name, "valid-name")

  def test_banned_names(self):
    with self.assertRaisesRegex(ValueError, "Invalid story name"):
      MockStory("-banned")

    with self.assertRaisesRegex(ValueError, "Invalid story name"):
      MockStory("#banned")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
