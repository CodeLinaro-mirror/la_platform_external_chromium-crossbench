# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import datetime as dt
import logging
import time
from typing import Sequence, Tuple

from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from crossbench import cli_helper
from crossbench.benchmarks.benchmark import SubStoryBenchmark, StoryFilter
from crossbench.browsers.webdriver import WebDriverBrowser
from crossbench.runner.run import Run
from crossbench.stories.story import Story

STORY_LIST = [
  "YoutubeFullscreen",
  "ZoomMeeting",
]

class PowerBenchmarkStory(Story, metaclass=abc.ABCMeta):

  @classmethod
  def all_story_names(cls) -> Sequence[str]:
    return STORY_LIST

  def __init__(self, name: str, duration_sec: float = 15*60):
    self._duration_sec = duration_sec
    self._driver = None
    super().__init__(name, dt.timedelta(seconds=duration_sec))

  def get_driver(self, run: Run) -> None:
    if isinstance(run.browser, WebDriverBrowser):
      self._driver = run.browser.driver
    else:
      raise TypeError("Power benchmark only supports WebDriverBrowser.")


class PowerBenchmarkStoryFilter(StoryFilter[PowerBenchmarkStory]):
  """
  Filter power benchmark stories by name.

  Syntax:
    "all"     Include all stories.
    "name"    Include story with the given name.
  """
  story_names: Sequence[str]

  def process_all(self, patterns: Sequence[str]) -> None:
    if len(patterns) == 1 and patterns[0] == "all":
      self.story_names = STORY_LIST
      return
    for story_name in patterns:
      assert story_name in STORY_LIST
    self.story_names = patterns

  def create_stories(self, separate: bool) -> Sequence[PowerBenchmarkStory]:
    stories = []
    for story_name in self.story_names:
      stories.append(globals()[story_name + "Story"](15*60))
    return stories


class ZoomMeetingStory(PowerBenchmarkStory):

  def __init__(self, duration_sec: float = 15*60):
    super().__init__("ZoomMeeting", duration_sec)

  def run(self, run: Run) -> None:
    self.get_driver(run)

    for _ in range(int(self._duration_sec/60)):
      self._driver.get("https://zoom.us/test")

      # Click the "Join" button
      btn = WebDriverWait(self._driver, 10).until(
          expected_conditions.element_to_be_clickable((By.ID, 'btnJoinTest')))
      btn.click()

      # Don't download the Zoom client, use Browser instead
      btn = WebDriverWait(self._driver, 15).until(
          expected_conditions.element_to_be_clickable(
              (By.XPATH, '//a[text()="Join from Your Browser"]')))
      btn.click()

      # Input name
      name = WebDriverWait(self._driver, 10).until(
          expected_conditions.element_to_be_clickable((By.ID, 'inputname')))
      name.send_keys('CBB Zoom Test')

      # Click the "Join" button
      btn = WebDriverWait(self._driver, 10).until(
          expected_conditions.element_to_be_clickable((By.ID, 'joinBtn')))
      btn.click()

      # Wait for 10 seconds to make sure to finish joining the meeting
      time.sleep(10)

      # Click the "Join Audio by Computer" button if it shows up.
      try:
        btn = WebDriverWait(self._driver, 10).until(
            expected_conditions.element_to_be_clickable(
                (By.XPATH, '//button[text()="Join Audio by Computer"]')))
        btn.click()
      except (TimeoutException, ElementNotInteractableException):
        logging.info("Join audio by comnputer button is not present.")
        pass

      # Start a new test meeting every 1 minute to avoid the meeting to be
      # ended by the Zoom host.
      time.sleep(60)


class YoutubeFullscreenStory(PowerBenchmarkStory):

  def click_button_by_xpath(self, xpath: str):
    """Find button by Xpath, click it when it's clickable."""
    btn = WebDriverWait(self._driver, 10).until(
        expected_conditions.element_to_be_clickable((By.XPATH, xpath)))
    btn.click()
    time.sleep(2)

  def set_resolution_to_1080p(self):
    """Set the video quality to 1080p."""
    # Click the "Settings" button
    self.click_button_by_xpath(
        '//button[@data-tooltip-target-id="ytp-settings-button"]')
    # Click the "Quality" button
    self.click_button_by_xpath('//div[text()="Quality"]')
    # CLick the "1080p" button
    self.click_button_by_xpath('//span[contains(string(), "1080p")]')

  def mute(self):
    """Mute the video."""
    btns = self._driver.find_elements(By.XPATH, '//button[@title="Mute (m)"]')
    if not btns:  # Already muted, since "Mute" button is not found
      return
    btns[0].click()
    time.sleep(2)

  def is_playing(self) -> bool:
    """Check if the video is playing."""
    # If there is no "Play" button, then the video is playing.
    btns = self._driver.find_elements(By.XPATH, '//button[@title="Play (k)"]')
    return not btns

  def playstop(self):
    """Play/Stop the video using shortcut key."""
    page = self._driver.find_element(By.TAG_NAME, 'body')
    page.send_keys('K')
    time.sleep(2)

  def fullscreen(self):
    """Switch fullscreen on/off using shortcut key."""
    page = self._driver.find_element(By.TAG_NAME, 'body')
    page.send_keys('F')
    time.sleep(2)

  def __init__(self, duration_sec: float = 15*60):
    super().__init__("YoutubeFullscreen", duration_sec)

  def run(self, run: Run) -> None:
    self.get_driver(run)

    self._driver.get("https://www.youtube.com/watch?v=rV_ERKtNyNA?t=1")
    time.sleep(10)

    # If the video is playing, stop it.
    if self.is_playing():
      self.playstop()

    self.mute()
    self.set_resolution_to_1080p()
    self.playstop()
    self.fullscreen()

    # Sleep while playing video
    time.sleep(self._duration_sec)


class PowerBenchmark(SubStoryBenchmark):
  """
  Benchmark runner for power benchmarks.
  """
  NAME = "powerbenchmark"
  DEFAULT_STORY_CLS = PowerBenchmarkStory
  STORY_FILTER_CLS = PowerBenchmarkStoryFilter

  def __init__(self, stories: Sequence[PowerBenchmarkStory]) -> None:
    for story in stories:
      assert isinstance(story, PowerBenchmarkStory)
    super().__init__(stories)

  @classmethod
  def aliases(cls) -> Tuple[str, ...]:
    return ("pb", "power") + super().aliases()
