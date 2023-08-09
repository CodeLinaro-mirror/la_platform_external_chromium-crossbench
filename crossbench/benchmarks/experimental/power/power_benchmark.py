# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import datetime as dt
import time
from typing import Sequence, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from crossbench.benchmarks.benchmark import Benchmark
from crossbench.browsers.webdriver import WebDriverBrowser
from crossbench.runner.run import Run
from crossbench.stories.story import Story

STORY_LIST = [
  "YoutubeFullscreen",
]

class PowerBenchmarkStory(Story, metaclass=abc.ABCMeta):

  @classmethod
  def all_story_names(cls) -> Sequence[str]:
    return STORY_LIST


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

  def __init__(self, duration_sec: float = 15):
    self.duration_sec = duration_sec
    self._driver = None
    super().__init__("YoutubeFullscreen", dt.timedelta(seconds=duration_sec))

  def run(self, run: Run) -> None:
    if isinstance(run.browser, WebDriverBrowser):
      self._driver = run.browser.driver
    else:
      raise TypeError("Power benchmark only supports WebDriverBrowser.")

    self._driver.get("https://www.youtube.com/watch?v=nP-nMZpLM1A")
    time.sleep(10)

    # If the video is playing, stop it.
    if self.is_playing():
      self.playstop()

    self.mute()
    self.set_resolution_to_1080p()
    self.playstop()
    self.fullscreen()

    # Sleep while playing video
    time.sleep(self.duration_sec)


class PowerBenchmark(Benchmark):
  """
  Benchmark runner for power benchmarks.
  """
  NAME = "powerbenchmark"
  DEFAULT_STORY_CLS = PowerBenchmarkStory

  def __init__(self):
    youtube = YoutubeFullscreenStory(15*60)
    super().__init__([youtube])

  @classmethod
  def aliases(cls) -> Tuple[str, ...]:
    return ("pb", "power") + super().aliases()
