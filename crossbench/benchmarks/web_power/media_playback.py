# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any, ClassVar

from typing_extensions import override

from crossbench.benchmarks.web_power.base import WebPowerBenchmarkBase, \
    WebPowerSiteConfig, WebPowerStory, WebPowerStoryFilter, _value_or
from crossbench.benchmarks.web_power.volume_helper import \
    AndroidVolumeController, VolumeMode
from crossbench.browsers.webdriver import WebDriverBrowser
from crossbench.parse import DurationParser

if TYPE_CHECKING:
  from crossbench.browsers.browser import Browser
  from crossbench.cli.parser import CBArgumentParser
  from crossbench.runner.actions import Actions
  from crossbench.runner.run import Run


class WebPowerMediaPlaybackStory(WebPowerStory):
  IS_SCENARIO_CLASS = True
  DEFAULT_DURATION: ClassVar[dt.timedelta] = dt.timedelta(seconds=120)
  DEFAULT_STABILIZATION_TIME: ClassVar[dt.timedelta] = dt.timedelta(seconds=10)
  DEFAULT_STATS: ClassVar[bool] = False
  DEFAULT_VOLUME: ClassVar[VolumeMode] = VolumeMode.ON

  @classmethod
  @override
  def story_name_cls(cls) -> str:
    return "media-playback"

  @classmethod
  @override
  def default_story_names(cls) -> tuple[str, ...]:
    return ("youtube",)

  def __init__(self,
               name_suffix: str,
               site_config: WebPowerSiteConfig,
               duration: dt.timedelta | None = None,
               stabilization_time: dt.timedelta | None = None,
               stats: bool | None = None,
               volume: VolumeMode | str | None = None) -> None:
    self.playback_duration = _value_or(duration, self.DEFAULT_DURATION)
    self.stabilization_time = _value_or(stabilization_time,
                                        self.DEFAULT_STABILIZATION_TIME)
    self.stats = _value_or(stats, self.DEFAULT_STATS)
    self.volume = _value_or(volume, self.DEFAULT_VOLUME)

    total_duration = (
        self.stabilization_time + self.setup_max_duration +
        self.playback_duration + WebPowerStory.DEFAULT_GRACE_PERIOD)
    super().__init__(name_suffix, site_config, total_duration)

  # This property guesstimates the maximum total duration of setup.
  # The alternative would have been to construct a self._recipe that consists
  # of commands, each with a run() method and a max_duration property.
  # However, that'd have been overkill (and less readable).
  @property
  def setup_max_duration(self) -> dt.timedelta:
    return dt.timedelta(seconds=20)

  def _wait_js_condition(self, actions: Actions, js_code: str) -> None:
    actions.wait_js_condition(js_code, min_interval=0.2, timeout=5.0)

  # TODO(eladalon): Move this simulated user gesture capability into the core of
  # Crossbench so standard actions can leverage it natively, and get rid of
  # the `noqa: SLF001` suppressions.
  def _evaluate_with_gesture(self, browser: Browser, js_code: str) -> Any:
    assert isinstance(browser, WebDriverBrowser), "Unsupported browser."
    result = browser._private_driver.execute_cdp_cmd(  # noqa: SLF001
        "Runtime.evaluate", {
            "expression": js_code,
            "returnByValue": True,
            "userGesture": True
        })
    return result["result"].get("value")

  def _click_element(self, actions: Actions, selector: str) -> None:
    self._wait_js_condition(actions, f"return !!({selector});")
    actions.js(f"({selector}).click();")

  def _by_aria_label(self, tag_type: str, label: str) -> str:
    return f"document.querySelector('{tag_type}[aria-label*=\"{label}\"]')"

  def _by_type_and_text(self, tag_type: str, text: str) -> str:
    return (f"Array.from(document.querySelectorAll('{tag_type}'))"
            f".find(el => el.textContent.trim() === '{text}')")

  def _video_selector(self) -> str:
    return "document.querySelector('video')"

  # Shows the main player UI overlay containing basic interaction buttons.
  # If the overlay is already visible, avoid toggling it off.
  def _show_controls(self, actions: Actions) -> None:
    settings = "document.querySelector('button[aria-label*=\"Settings\"]')"
    # If the Settings button is hidden, click the video to show controls.
    if actions.js(f"let el = {settings}; "
                  f"return !el || el.offsetParent === null;"):
      self._click_element(actions, self._video_selector())

  # Opens the settings bottom sheet menu containing playback parameters
  # (e.g. video quality, stats for nerds, ambient mode toggles).
  def _enter_settings(self, actions: Actions) -> None:
    self._show_controls(actions)
    self._click_element(
        actions, "document.querySelector('button[aria-label*=\"Settings\"]')")

  def _set_video_time(self, actions: Actions, target_time: int) -> None:
    self._wait_js_condition(actions, f"return !!({self._video_selector()});")
    actions.js(f"{self._video_selector()}.currentTime = {target_time};")

  def _control_video(self, actions: Actions, command: str) -> None:
    # Wait for the video element to render in the DOM.
    self._wait_js_condition(actions, f"return !!({self._video_selector()});")
    actions.js(f"{self._video_selector()}.{command}();")
    actions.wait(dt.timedelta(seconds=1.0))

  def _pause_video(self, actions: Actions) -> None:
    self._control_video(actions, "pause")

  def _resume_video(self, actions: Actions) -> None:
    self._control_video(actions, "play")

  @override
  def setup(self, run: Run) -> None:
    super().setup(run)
    if self.volume != VolumeMode.UNCHANGED:
      if not run.browser_platform.is_android:
        raise ValueError(
            f"The --volume={self.volume} option is only supported on Android, "
            f"but the active platform is {run.browser_platform}.")
      AndroidVolumeController(run.browser_platform).configure_volume(
          self.volume)

    with run.actions("Show_URL", verbose=True) as actions:
      actions.show_url(self.url)

    if self.stabilization_time.total_seconds() > 0:
      with run.actions("Stabilization", verbose=True) as actions:
        actions.wait(self.stabilization_time)

    with run.actions("Consent_Banner", verbose=True) as actions:
      # Wait for the initial page to load, click 'Accept', and programmatically
      # block until the cookie-save page reload fully completes.
      # The reload context-switch naturally clears window.__waiting_for_reload.
      self._wait_js_condition(actions,
                              "return document.readyState === 'complete';")
      actions.js("window.__waiting_for_reload = true;")
      self._click_element(actions, self._by_aria_label("button", "Accept"))
      self._wait_js_condition(actions, "return !window.__waiting_for_reload;")
      self._wait_js_condition(actions,
                              "return document.readyState === 'complete';")

    with run.actions("Focus_Tap", verbose=True) as actions:
      self._click_element(actions, self._video_selector())

    with run.actions("Pause_Video", verbose=True) as actions:
      self._pause_video(actions)

    with run.actions("Full_Screen", verbose=True) as actions:
      self._show_controls(actions)
      selector = "document.querySelector('button[aria-label*=\"screen\"]')"
      self._wait_js_condition(actions, f"return !!({selector});")
      self._evaluate_with_gesture(run.browser, f"({selector}).click();")

    if self.stats:
      with run.actions("Stats_For_Nerds", verbose=True) as actions:
        self._enter_settings(actions)
        self._click_element(actions,
                            self._by_type_and_text("span", "Stats For Nerds"))

    with run.actions("Set_Quality", verbose=True) as actions:
      self._enter_settings(actions)
      self._click_element(actions, self._by_type_and_text("span", "Quality"))
      self._click_element(actions, self._by_type_and_text("span", "1080p"))

    with run.actions("Turn_Off_Ambient", verbose=True) as actions:
      self._enter_settings(actions)
      self._click_element(actions,
                          self._by_type_and_text("span", "Ambient mode"))

    with run.actions("Seek_To_Start", verbose=True) as actions:
      self._show_controls(actions)
      self._set_video_time(actions, 0)

    with run.actions("Resume_Playback", verbose=True) as actions:
      self._resume_video(actions)

  @override
  def run(self, run: Run) -> None:
    with run.actions(
        "Media_Playback",
        verbose=True,
        performance_mark=WebPowerStory.MEASUREMENT_MARK) as actions:
      actions.wait(self.playback_duration)


class WebPowerMediaPlaybackStoryFilter(
    WebPowerStoryFilter[WebPowerMediaPlaybackStory]):
  """Story filter for Web Power media-playback stories."""

  IS_SCENARIO_CLASS = True
  STORY_CLS = WebPowerMediaPlaybackStory


class WebPowerMediaPlaybackBenchmark(WebPowerBenchmarkBase):
  """Benchmark runner for Power Media Playback scenario."""

  IS_SCENARIO_CLASS = True
  NAME: ClassVar = f"{WebPowerBenchmarkBase.NAME}-media-playback"
  DEFAULT_STORY_CLS: ClassVar = WebPowerMediaPlaybackStory
  STORY_FILTER_CLS: ClassVar = WebPowerMediaPlaybackStoryFilter
  SITE_REQUIRED: ClassVar[bool] = False
  REQUIRES_AUTOPLAY: ClassVar[bool] = True

  @classmethod
  @override
  def add_cli_arguments(cls, parser: CBArgumentParser) -> CBArgumentParser:
    parser = super().add_cli_arguments(parser)
    story_cls = cls.DEFAULT_STORY_CLS
    parser.set_defaults(
        duration=story_cls.DEFAULT_DURATION,
        stabilization_time=story_cls.DEFAULT_STABILIZATION_TIME,
    )
    return parser

  @classmethod
  @override
  def add_scenario_cli_arguments(cls,
                                 parser: CBArgumentParser) -> CBArgumentParser:
    story_cls = cls.DEFAULT_STORY_CLS
    # TODO(eladalon): Avoid accessing private option_string_actions.
    actions = parser._option_string_actions  # noqa: SLF001
    if "--duration" not in actions:
      parser.add_argument(
          "--duration",
          type=DurationParser.positive_duration,
          help="How long to play the video for.",
      )
    if "--stabilization-time" not in actions:
      parser.add_argument(
          "--stabilization",
          "--stabilization-time",
          dest="stabilization_time",
          type=DurationParser.positive_or_zero_duration,
          help="How long to wait after setting up page/playback to stabilize.",
      )
    parser.add_argument(
        "--stats",
        action="store_true",
        default=story_cls.DEFAULT_STATS,
        help="Enable 'Stats for Nerds' overlay during playback. "
        f"(Default: {str(story_cls.DEFAULT_STATS).lower()})")
    parser.add_argument(
        "--volume",
        type=VolumeMode,
        choices=tuple(VolumeMode),
        default=story_cls.DEFAULT_VOLUME,
        help="Configure device music stream volume. "
        f"(Default: {story_cls.DEFAULT_VOLUME})")
    return parser
