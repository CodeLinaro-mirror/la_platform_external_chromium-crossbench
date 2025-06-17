# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import abc
import argparse
import datetime as dt
import logging
from typing import Any, Optional, Tuple

from typing_extensions import override

from crossbench import config
from crossbench import path as pth
from crossbench.benchmarks.base import Benchmark
from crossbench.browsers.attributes import BrowserAttributes
from crossbench.cli.parser import CrossBenchArgumentParser
from crossbench.cli.ui import timer
from crossbench.flags.base import Flags
from crossbench.helper import input_helper
from crossbench.parse import DurationParser
from crossbench.runner.run import Run
from crossbench.stories.story import Story

PLAY_AUDIO_SCRIPT = """

setTimeout(()=>{
  document.getElementById('unmuteButton').click();
}, 1000);

"""

class PowerlineStory(Story, metaclass=abc.ABCMeta):

  STORY_NAME="podcast"
  URL="http://localhost:8000"

  def __init__(self, run_for: Optional[dt.timedelta] = dt.timedelta()):
    duration = (run_for or dt.timedelta(seconds=600))
    self._run_for = duration
    super().__init__(self.STORY_NAME, duration)

  def run(self, run: Run) -> None:
    with timer():
      with run.actions("Show URL") as actions:
        actions.show_url(self.URL)
      with run.actions("Autoplay") as actions:
        actions.wait(dt.timedelta(seconds=5))
        actions.js(PLAY_AUDIO_SCRIPT)
      with run.actions("Screen") as actions:
        actions.wait(dt.timedelta(seconds=5))
        actions.platform.sh("input", "keyevent", "26")
      self._wait_for_input()
      logging.info("Stopping benchmark...")

  def _wait_for_input(self) -> None:
    logging.critical(
        "Measurement has started. The browser will close in %s" +
        " (or press enter to close immediately)", self._run_for)
    try:
      input_helper.input_with_timeout(timeout=self._run_for)
    except KeyboardInterrupt:
      pass

  @classmethod
  @override
  def all_story_names(cls) -> Tuple[str, ...]:
    return (PowerlineStory.STORY_NAME,)



class PowerlineBenchmark(Benchmark, metaclass=abc.ABCMeta):
  """
  Benchmark runner for the Powerline background power-consumption test.

  This test opens up an HTML5 page which plays an audio, intended to simulate
  listening to a podcast with the screen off. The test measures the CPU power
  consumption on the Pixel power rails via Perfetto.
  """
  NAME="powerline"
  DEFAULT_STORY_CLS = PowerlineStory

  # TODO: we may want to check somehow that the device is a Pixel and therefore
  # has meaningful power rails we can read.
  # TODO: we may want to unlock the device so we can run further benchmarks
  # on it without manual intervention.

  def __init__(self,
               run_for: Optional[dt.timedelta] = None) -> None:
    powerline_story = PowerlineStory(run_for)
    super().__init__([powerline_story])

  @classmethod
  def _base_dir(cls) -> pth.LocalPath:
    return config.config_dir() / "benchmark" / "powerline"

  @classmethod
  @override
  def default_network_config_path(cls) -> pth.LocalPath:
    return cls._base_dir() / "network_config.hjson"

  @classmethod
  @override
  def default_probe_config_path(cls) -> pth.LocalPath:
    return cls._base_dir() / "probe_config.hjson"

  @classmethod
  @override
  def extra_flags(cls, browser_attributes: BrowserAttributes) -> Flags:
    # This flag is required because Chrome a) does not autoplay based on the
    #  HTML5 tag and b) it will not play from JavaScript if the user does not
    # interact with the page first. https://developer.chrome.com/blog/autoplay
    assert browser_attributes.is_chromium_based
    return Flags({"--autoplay-policy": "no-user-gesture-required"})

  @classmethod
  @override
  def add_cli_parser(
    cls, subparsers: argparse.ArgumentParser) -> CrossBenchArgumentParser:
    parser = super().add_cli_parser(subparsers)
    parser.add_argument(
        "--run-for",
        "--stop-after",
        "--duration",
        type=DurationParser.positive_duration,
        help="How long to run the power measurements for")
    return parser

  @classmethod
  @override
  def kwargs_from_cli(cls, args: argparse.Namespace) -> dict[str, Any]:
    kwargs = super().kwargs_from_cli(args)
    kwargs["run_for"] = args.run_for
    return kwargs
