# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

from crossbench.stories import Story

from .action import Action
from .playback_controller import PlaybackController

if TYPE_CHECKING:
  from crossbench.runner import Run


class Page(Story, metaclass=abc.ABCMeta):

  url: Optional[str]

  @classmethod
  def all_story_names(cls) -> Tuple[str, ...]:
    return tuple(page.name for page in PAGE_LIST)

  def __init__(self,
               name: str,
               duration: float,
               playback: Optional[PlaybackController] = None):
    self._playback = playback or PlaybackController.once()
    super().__init__(name, duration)

  def set_parent(self, parent: Page) -> None:
    # TODO: support nested playback controllers.
    self._playback = PlaybackController.once()
    del parent


class LivePage(Page):
  url: str

  def __init__(self,
               name: str,
               url: str,
               duration: float = 15,
               playback: Optional[PlaybackController] = None) -> None:
    super().__init__(name, duration, playback)
    assert url, "Invalid page url"
    self.url: str = url

  def details_json(self) -> Dict[str, Any]:
    result = super().details_json()
    result["url"] = str(self.url)
    return result

  def run(self, run: Run) -> None:
    for _ in self._playback:
      run.browser.show_url(run.runner, self.url)
      run.runner.wait(self.duration + 1)

  def __str__(self) -> str:
    return f"Page(name={self.name}, url={self.url})"


class CombinedPage(Page):

  def __init__(self,
               pages: Sequence[Page],
               name: str = "combined",
               playback: Optional[PlaybackController] = None):
    assert len(pages), "No sub-pages provided for CombinedPage"
    assert len(pages) > 1, "Combined Page needs more than one page"
    self._pages = pages
    for page in self._pages:
      page.set_parent(self)
    duration = sum(page.duration for page in pages)
    super().__init__(name, duration, playback)
    self.url = None

  def details_json(self) -> Dict[str, Any]:
    result = super().details_json()
    result["pages"] = list(page.details_json() for page in self._pages)
    return result

  def run(self, run: Run) -> None:
    for _ in self._playback:
      for page in self._pages:
        page.run(run)

  def __str__(self) -> str:
    combined_name = ",".join(page.name for page in self._pages)
    return f"CombinedPage({combined_name})"


class InteractivePage(Page):

  def __init__(self,
               actions: List[Action],
               name: str,
               playback: Optional[PlaybackController] = None):
    self._name = name
    assert isinstance(actions, list)
    self._actions = actions
    assert self._actions, "Must have at least 1 valid action"
    duration = self._get_duration()
    super().__init__(name, duration, playback)

  @property
  def actions(self) -> List[Action]:
    return self._actions

  def run(self, run: Run) -> None:
    for _ in self._playback:
      for action in self._actions:
        action.run(run, self)

  def details_json(self) -> Dict[str, Any]:
    result = super().details_json()
    result["actions"] = list(action.details_json() for action in self._actions)
    return result

  def _get_duration(self) -> float:
    duration: float = 0
    for action in self._actions:
      if action.duration is not None:
        duration += action.duration
    return duration


PAGE_LIST = (
    LivePage("amazon", "https://www.amazon.de/s?k=heizkissen", 5),
    LivePage("bing", "https://www.bing.com/images/search?q=not+a+squirrel", 5),
    LivePage("caf", "http://www.caf.fr", 6),
    LivePage("cnn", "https://cnn.com/", 7),
    LivePage("ecma262", "https://tc39.es/ecma262/#sec-numbers-and-dates", 10),
    LivePage("expedia", "https://www.expedia.com/", 7),
    LivePage("facebook", "https://facebook.com/shakira", 8),
    LivePage("maps", "https://goo.gl/maps/TEZde4y4Hc6r2oNN8", 10),
    LivePage("microsoft", "https://microsoft.com/", 6),
    LivePage("provincial", "http://www.provincial.com", 6),
    LivePage("sueddeutsche", "https://www.sueddeutsche.de/wirtschaft", 8),
    LivePage("timesofindia", "https://timesofindia.indiatimes.com/", 8),
    LivePage("twitter", "https://twitter.com/wernertwertzog?lang=en", 6),
)
PAGES = {page.name: page for page in PAGE_LIST}
PAGE_LIST_SMALL = (PAGES["facebook"], PAGES["maps"], PAGES["timesofindia"],
                   PAGES["cnn"])
