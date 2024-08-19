# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import datetime as dt
import logging

from typing import TYPE_CHECKING, Optional, Sequence, Tuple, Iterable

from crossbench.benchmarks.loading.action_runner.base import \
    ActionNotImplementedError
from crossbench.benchmarks.loading.action_runner.basic_action_runner import \
    BasicActionRunner
from crossbench.benchmarks.loading.playback_controller import \
    PlaybackController
from crossbench.benchmarks.loading.tab_controller import \
    TabController
from crossbench.stories.story import Story

if TYPE_CHECKING:
  from crossbench.benchmarks.loading.action_runner.base import ActionRunner
  from crossbench.benchmarks.loading.page_config import ActionBlock
  from crossbench.runner.run import Run
  from crossbench.types import JsonDict

DEFAULT_DURATION_SECONDS = 15
DEFAULT_DURATION = dt.timedelta(seconds=DEFAULT_DURATION_SECONDS)


class Page(Story, metaclass=abc.ABCMeta):

  url: Optional[str]

  @classmethod
  def all_story_names(cls) -> Tuple[str, ...]:
    return tuple(page.name for page in PAGE_LIST)

  def __init__(self,
               name: str,
               duration: dt.timedelta = DEFAULT_DURATION,
               playback: PlaybackController = PlaybackController.default(),
               tabs: TabController = TabController.default(),
               action_runner: Optional[ActionRunner] = None,
               about_blank_duration: dt.timedelta = dt.timedelta()):
    self._playback: PlaybackController = playback
    self._tabs: TabController = tabs
    self._action_runner: ActionRunner = action_runner or BasicActionRunner()
    self._about_blank_duration = about_blank_duration
    super().__init__(name, duration)

  @property
  def action_runner(self) -> ActionRunner:
    return self._action_runner

  def set_parent(self, parent: Page) -> None:
    # TODO: support nested playback controllers.
    self._playback = PlaybackController.default()
    self._tabs = TabController.default()
    del parent

  def _maybe_navigate_to_about_blank(self, run: Run) -> None:
    if duration := self._about_blank_duration:
      run.browser.show_url(run.runner, "about:blank")
      run.runner.wait(duration)

  @abc.abstractmethod
  def run_with(self, run: Run, action_runner: ActionRunner) -> None:
    pass


class LivePage(Page):
  url: str

  def __init__(
      self,
      name: str,
      url: str,
      duration: dt.timedelta = DEFAULT_DURATION,
      playback: PlaybackController = PlaybackController.default(),
      tabs: TabController = TabController.default(),
      action_runner: Optional[ActionRunner] = None,
      about_blank_duration: dt.timedelta = dt.timedelta()
  ) -> None:
    super().__init__(name, duration, playback, tabs, action_runner,
                     about_blank_duration)
    assert url, "Invalid page url"
    self.url: str = url

  def set_duration(self, duration: dt.timedelta) -> None:
    self._duration = duration

  def details_json(self) -> JsonDict:
    result = super().details_json()
    result["url"] = str(self.url)
    return result

  def run(self, run: Run) -> None:
    for _ in self._playback:
      self.action_runner.run_page(run, self)

  def run_with(self, run: Run, action_runner: ActionRunner) -> None:
    action_runner.run_page(run, self)

  def __str__(self) -> str:
    return f"Page(name={self.name}, url={self.url})"


class CombinedPage(Page):

  def __init__(self,
               pages: Iterable[Page],
               name: str = "combined",
               playback: PlaybackController = PlaybackController.default(),
               tabs: TabController = TabController.default(),
               action_runner: Optional[ActionRunner] = None,
               about_blank_duration: dt.timedelta = dt.timedelta()):
    self._pages = tuple(pages)
    assert self._pages, "No sub-pages provided for CombinedPage"
    assert len(self._pages) > 1, "Combined Page needs more than one page"
    self._tabs = tabs

    duration = dt.timedelta()
    for page in self._pages:
      page.set_parent(self)
      duration += page.duration
    super().__init__(name, duration, playback, tabs, action_runner,
                     about_blank_duration)
    self.url = None
    self.validate_action_runner()

  @property
  def pages(self) -> Iterable[Page]:
    return self._pages

  def details_json(self) -> JsonDict:
    result = super().details_json()
    result["pages"] = list(page.details_json() for page in self._pages)
    return result

  def validate_action_runner(self) -> None:
    for page in self._pages:
      if isinstance(page, InteractivePage):
        if type(page.action_runner) is not type(self.action_runner):
          raise TypeError(
              f"Type of action_runner of sub pages should be the same. "
              f"Type should be {type(self.action_runner)}, "
              f"but got {type(page.action_runner)}")

  def run(self, run: Run) -> None:
    for _ in self._playback:
      self.action_runner.run_combined_page(run, self)

  def run_with(self, run: Run, action_runner: ActionRunner) -> None:
    action_runner.run_combined_page(run, self)

  def __str__(self) -> str:
    combined_name = ",".join(page.name for page in self._pages)
    return f"CombinedPage({combined_name})"


class InteractivePage(Page):

  def __init__(self,
               action_blocks: Tuple[ActionBlock, ...],
               name: str,
               playback: PlaybackController = PlaybackController.default(),
               tabs: TabController = TabController.default(),
               action_runner: Optional[ActionRunner] = None,
               about_blank_duration: dt.timedelta = dt.timedelta()):
    self._name: str = name
    assert isinstance(action_blocks, tuple)
    self._action_blocks: Tuple[ActionBlock, ...] = action_blocks
    assert self._action_blocks, "Must have at least 1 valid action"
    duration = self._get_duration()
    super().__init__(self._name, duration, playback, tabs, action_runner,
                     about_blank_duration)

  @property
  def action_blocks(self) -> Tuple[ActionBlock, ...]:
    return self._action_blocks

  @property
  def action_runner(self) -> ActionRunner:
    return self._action_runner

  @action_runner.setter
  def action_runner(self, action_runner: ActionRunner) -> None:
    assert isinstance(self._action_runner, BasicActionRunner)
    self._action_runner = action_runner

  def failure_screenshot(self, run: Run) -> None:
    try:
      self.action_runner.screenshot_impl(run, "failure")
    except ActionNotImplementedError:
      logging.debug("Skipping failure screenshot, action not implemented")
    except Exception as e:
      logging.error("Failed to take a failure screenshot: %s", str(e))

  def run(self, run: Run) -> None:
    for _ in self._playback:
      self.action_runner.run_interactive_page(run, self)

  def run_with(self, run: Run, action_runner: ActionRunner) -> None:
    action_runner.run_interactive_page(run, self)

  def details_json(self) -> JsonDict:
    result = super().details_json()
    result["actions"] = list(block.to_json() for block in self._action_blocks)
    return result

  def _get_duration(self) -> dt.timedelta:
    duration = dt.timedelta()
    for block in self._action_blocks:
      duration += block.duration
    return duration


PAGE_LIST = (
    LivePage("blank", "about:blank", dt.timedelta(seconds=1)),
    LivePage("amazon", "https://www.amazon.de/s?k=heizkissen",
             dt.timedelta(seconds=5)),
    LivePage("bing", "https://www.bing.com/images/search?q=not+a+squirrel",
             dt.timedelta(seconds=5)),
    LivePage("caf", "http://www.caf.fr", dt.timedelta(seconds=6)),
    LivePage("cnn", "https://cnn.com/", dt.timedelta(seconds=7)),
    LivePage("ecma262", "https://tc39.es/ecma262/#sec-numbers-and-dates",
             dt.timedelta(seconds=10)),
    LivePage("expedia", "https://www.expedia.com/", dt.timedelta(seconds=7)),
    LivePage("facebook", "https://facebook.com/shakira",
             dt.timedelta(seconds=8)),
    LivePage("maps", "https://goo.gl/maps/TEZde4y4Hc6r2oNN8",
             dt.timedelta(seconds=10)),
    LivePage("microsoft", "https://microsoft.com/", dt.timedelta(seconds=6)),
    LivePage("provincial", "http://www.provincial.com",
             dt.timedelta(seconds=6)),
    LivePage("sueddeutsche", "https://www.sueddeutsche.de/wirtschaft",
             dt.timedelta(seconds=8)),
    LivePage("theverge", "https://www.theverge.com/", dt.timedelta(seconds=10)),
    LivePage("timesofindia", "https://timesofindia.indiatimes.com/",
             dt.timedelta(seconds=8)),
    LivePage("twitter", "https://twitter.com/wernertwertzog?lang=en",
             dt.timedelta(seconds=6)),
)
PAGES = {page.name: page for page in PAGE_LIST}
PAGE_LIST_SMALL = (PAGES["facebook"], PAGES["maps"], PAGES["timesofindia"],
                   PAGES["cnn"])
