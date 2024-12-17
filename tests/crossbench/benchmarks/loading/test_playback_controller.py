# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt
import unittest

from crossbench.benchmarks.loading.playback_controller import (
    ForeverPlaybackController, PlaybackController, RepeatPlaybackController,
    TimeoutPlaybackController)
from tests import test_helper


class PlaybackControllerTestCase(unittest.TestCase):

  def test_parse_invalid(self):
    for invalid in [
        "11", "something", "1.5x", "4.3.h", "4.5.x", "-1x", "-1.4x", "-2h",
        "-2.1h", "1h30", "infx", "infh", "nanh", "nanx", "0s", "0"
    ]:
      with self.subTest(pattern=invalid):
        with self.assertRaises((argparse.ArgumentTypeError, ValueError)):
          PlaybackController.parse(invalid)

  def test_invalid_repeat(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      PlaybackController.repeat(-1)

  def test_parse_repeat(self):
    playback = PlaybackController.parse("once")
    self.assertIsInstance(playback, RepeatPlaybackController)
    assert isinstance(playback, RepeatPlaybackController)
    self.assertEqual(playback.count, 1)
    self.assertEqual(len(list(playback)), 1)

    playback = PlaybackController.parse("1x")
    self.assertIsInstance(playback, RepeatPlaybackController)
    assert isinstance(playback, RepeatPlaybackController)
    self.assertEqual(playback.count, 1)
    self.assertEqual(len(list(playback)), 1)

    playback = PlaybackController.parse("11x")
    self.assertIsInstance(playback, RepeatPlaybackController)
    assert isinstance(playback, RepeatPlaybackController)
    self.assertEqual(playback.count, 11)
    self.assertEqual(len(list(playback)), 11)

  def test_parse_forever(self):
    playback = PlaybackController.parse("forever")
    self.assertIsInstance(playback, ForeverPlaybackController)
    playback = PlaybackController.parse("inf")
    self.assertIsInstance(playback, ForeverPlaybackController)
    playback = PlaybackController.parse("infinity")
    self.assertIsInstance(playback, ForeverPlaybackController)

  def test_parse_duration(self):
    playback = PlaybackController.parse("5s")
    self.assertIsInstance(playback, TimeoutPlaybackController)
    assert isinstance(playback, TimeoutPlaybackController)
    self.assertEqual(playback.duration, dt.timedelta(seconds=5))

    playback = PlaybackController.parse("5m")
    self.assertIsInstance(playback, TimeoutPlaybackController)
    assert isinstance(playback, TimeoutPlaybackController)
    self.assertEqual(playback.duration, dt.timedelta(minutes=5))

    playback = PlaybackController.parse("5.5m")
    self.assertIsInstance(playback, TimeoutPlaybackController)
    assert isinstance(playback, TimeoutPlaybackController)
    self.assertEqual(playback.duration, dt.timedelta(minutes=5.5))

    playback = PlaybackController.parse("5.5m")
    self.assertIsInstance(playback, TimeoutPlaybackController)
    assert isinstance(playback, TimeoutPlaybackController)
    self.assertEqual(playback.duration, dt.timedelta(minutes=5.5))

  def test_once(self):
    iterations = sum(1 for _ in PlaybackController.once())
    self.assertEqual(iterations, 1)
    iterations = sum(1 for _ in PlaybackController.default())
    self.assertEqual(iterations, 1)

  def test_repeat(self):
    iterations = sum(1 for _ in PlaybackController.repeat(1))
    self.assertEqual(iterations, 1)
    iterations = sum(1 for _ in PlaybackController.repeat(11))
    self.assertEqual(iterations, 11)

  def test_timeout(self):
    # Even 0-duration playback should run once
    iterations = sum(1 for _ in PlaybackController.timeout(dt.timedelta()))
    self.assertEqual(iterations, 1)
    iterations = sum(
        1 for _ in PlaybackController.timeout(dt.timedelta(milliseconds=0.1)))
    self.assertGreaterEqual(iterations, 1)

  def test_forever(self):
    count = 0
    for _ in PlaybackController.forever():
      # Just run for some large-ish amount of iterations to get code coverage.
      count += 1
      if count > 100:
        break


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
