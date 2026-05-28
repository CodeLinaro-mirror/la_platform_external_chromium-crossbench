# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from crossbench import exception
from crossbench.runner.groups.browsers import BrowsersRunGroup
from crossbench.runner.groups.cache_temperatures import \
    CacheTemperaturesRunGroup
from crossbench.runner.groups.repetitions import RepetitionsRunGroup
from crossbench.runner.groups.stories import StoriesRunGroup
from tests import test_helper
from tests.crossbench.runner.groups.base import BaseRunGroupTestCase
from tests.crossbench.runner.helper import MockRun

if TYPE_CHECKING:
  from crossbench.runner.run import Run


class RunGroupTestCase(BaseRunGroupTestCase):

  def create_groups(self, runs: Iterable[Run], throw: bool = True):
    cache_temperatures_groups = CacheTemperaturesRunGroup.groups(
        runs, throw=throw)
    repetitions_groups = RepetitionsRunGroup.groups(cache_temperatures_groups,
                                                    throw)
    story_groups = StoriesRunGroup.groups(repetitions_groups, throw)
    browser_group = BrowsersRunGroup(story_groups, throw)
    return browser_group

  def test_create_empty(self):
    with self.assertRaises(ValueError):
      self.create_groups([])

  def test_create_single(self):
    session = self.default_session(throw=True)
    run_0 = MockRun(self.runner, session, "story 0")
    browser_group = self.create_groups([run_0])
    self.assertListEqual(list(browser_group.runs), [run_0])
    story_groups = list(browser_group.story_groups)
    self.assertEqual(len(story_groups), 1)
    self.assertListEqual(list(story_groups[0].runs), [run_0])
    repetitions_group = list(story_groups[0].repetitions_groups)
    self.assertEqual(len(repetitions_group), 1)

  def test_single_story_multiple_repetitions(self):
    session = self.default_session(throw=True)
    run_0 = MockRun(self.runner, session, "story 0", None, repetition=0)
    run_1 = MockRun(self.runner, session, "story 0", None, repetition=1)
    browser_group = self.create_groups([run_0, run_1])
    self.assertListEqual(list(browser_group.runs), [run_0, run_1])
    story_groups = list(browser_group.story_groups)
    self.assertEqual(len(story_groups), 1)
    repetitions_groups = list(story_groups[0].repetitions_groups)
    self.assertEqual(len(repetitions_groups), 1)
    repetitions_group = repetitions_groups[0]
    cache_temp_groups = list(repetitions_group.cache_temperatures_groups)
    self.assertEqual(len(cache_temp_groups), 2)
    self.assertListEqual(list(cache_temp_groups[0].runs), [run_0])
    self.assertListEqual(list(cache_temp_groups[1].runs), [run_1])
    cache_temp_repetitions_group = list(
        repetitions_group.cache_temperature_repetitions_groups)
    self.assertEqual(len(cache_temp_repetitions_group), 1)
    self.assertListEqual(
        list(cache_temp_repetitions_group[0].runs), [run_0, run_1])
    self.assertEqual(cache_temp_repetitions_group[0].cache_temperature,
                     "default")

  def test_single_story_multiple_repetitions_cache_temperatures(self):
    session = self.default_session(throw=True)
    run_0 = MockRun(
        self.runner, session, "story 0", None, repetition=0, temperature="cold")
    run_1 = MockRun(
        self.runner, session, "story 0", None, repetition=0, temperature="warm")
    run_2 = MockRun(
        self.runner, session, "story 0", None, repetition=1, temperature="cold")
    run_3 = MockRun(
        self.runner, session, "story 0", None, repetition=1, temperature="warm")

    browser_group = self.create_groups([run_0, run_1, run_2, run_3])
    self.assertListEqual(list(browser_group.runs), [run_0, run_1, run_2, run_3])
    story_groups = list(browser_group.story_groups)
    self.assertEqual(len(story_groups), 1)
    repetitions_groups = list(story_groups[0].repetitions_groups)
    self.assertEqual(len(repetitions_groups), 1)
    repetitions_group = repetitions_groups[0]
    cache_temp_groups = list(repetitions_group.cache_temperatures_groups)
    self.assertEqual(len(cache_temp_groups), 2)
    self.assertListEqual(list(cache_temp_groups[0].runs), [run_0, run_1])
    self.assertListEqual(list(cache_temp_groups[1].runs), [run_2, run_3])
    cache_temp_repetitions_group = list(
        repetitions_group.cache_temperature_repetitions_groups)
    self.assertEqual(len(cache_temp_groups), 2)
    self.assertListEqual(
        list(cache_temp_repetitions_group[0].runs), [run_0, run_2])
    self.assertListEqual(
        list(cache_temp_repetitions_group[1].runs), [run_1, run_3])
    self.assertEqual(cache_temp_repetitions_group[0].cache_temperature, "cold")
    self.assertEqual(cache_temp_repetitions_group[1].cache_temperature, "warm")

  def test_all_exceptions(self):
    session = self.default_session(throw=False)
    # 2 runs sharing the same session to verify session exception deduplication
    run_0 = MockRun(self.runner, session, "story 0", repetition=0)
    run_0._exceptions = exception.Annotator(throw=False)
    run_0._exceptions.append(ValueError("Run 0 error"))

    run_1 = MockRun(self.runner, session, "story 0", repetition=1)
    run_1._exceptions = exception.Annotator(throw=False)
    run_1._exceptions.append(TypeError("Run 1 error"))

    session._exceptions.append(RuntimeError("Session error"))

    cache_temperatures_groups = list(
        CacheTemperaturesRunGroup.groups([run_0, run_1], throw=False))
    cache_temperatures_groups[0].exceptions.append(KeyError("Cache error"))

    exc_types_cache = [
        type(e.exception) for e in cache_temperatures_groups[0].all_exceptions
    ]
    self.assertIn(KeyError, exc_types_cache)
    self.assertIn(ValueError, exc_types_cache)
    self.assertIn(RuntimeError, exc_types_cache)
    self.assertEqual(exc_types_cache.count(RuntimeError), 1)

    repetitions_groups = list(
        RepetitionsRunGroup.groups(cache_temperatures_groups, throw=False))
    repetitions_groups[0].exceptions.append(IndexError("Repetition error"))

    exc_types_rep = [
        type(e.exception) for e in repetitions_groups[0].all_exceptions
    ]
    self.assertIn(IndexError, exc_types_rep)
    self.assertIn(KeyError, exc_types_rep)
    self.assertIn(ValueError, exc_types_rep)
    self.assertIn(TypeError, exc_types_rep)
    self.assertIn(RuntimeError, exc_types_rep)
    self.assertEqual(exc_types_rep.count(RuntimeError), 1)

    story_groups = list(StoriesRunGroup.groups(repetitions_groups, throw=False))
    story_groups[0].exceptions.append(AttributeError("Story error"))

    exc_types_story = [
        type(e.exception) for e in story_groups[0].all_exceptions
    ]
    self.assertIn(AttributeError, exc_types_story)
    self.assertIn(IndexError, exc_types_story)
    self.assertIn(KeyError, exc_types_story)
    self.assertIn(ValueError, exc_types_story)
    self.assertIn(TypeError, exc_types_story)
    self.assertIn(RuntimeError, exc_types_story)
    self.assertEqual(exc_types_story.count(RuntimeError), 1)

    browser_group = BrowsersRunGroup(story_groups, throw=False)
    browser_group.exceptions.append(EOFError("Browser error"))

    exc_types_browser = [
        type(e.exception) for e in browser_group.all_exceptions
    ]
    self.assertIn(EOFError, exc_types_browser)
    self.assertIn(AttributeError, exc_types_browser)
    self.assertIn(IndexError, exc_types_browser)
    self.assertIn(KeyError, exc_types_browser)
    self.assertIn(ValueError, exc_types_browser)
    self.assertIn(TypeError, exc_types_browser)
    self.assertIn(RuntimeError, exc_types_browser)
    self.assertEqual(exc_types_browser.count(RuntimeError), 1)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
