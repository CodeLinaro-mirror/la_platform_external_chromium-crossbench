# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any, ClassVar

from typing_extensions import override

from crossbench.benchmarks.web_power.base import WebPowerBenchmarkBase, \
    WebPowerStory, _value_or
from crossbench.browsers.webdriver import WebDriverBrowser
from crossbench.parse import DurationParser

if TYPE_CHECKING:
  import argparse

  from crossbench.browsers.browser import Browser
  from crossbench.cli.parser import CBArgumentParser
  from crossbench.runner.actions import Actions
  from crossbench.runner.run import Run


class WebPowerMediaPlaybackStory(WebPowerStory):
  DEFAULT_DURATION: ClassVar[dt.timedelta] = dt.timedelta(seconds=120)
  DEFAULT_STABILIZATION_TIME: ClassVar[dt.timedelta] = dt.timedelta(seconds=10)
  DEFAULT_STATS: ClassVar[bool] = False

  @property
  @override
  def story_name(self) -> str:
    return "media-playback"

  def __init__(self,
               name_suffix: str,
               url: str,
               playback_duration: dt.timedelta | None = None,
               stabilization_time: dt.timedelta | None = None,
               stats: bool | None = None) -> None:
    self.playback_duration = _value_or(playback_duration, self.DEFAULT_DURATION)
    self.stabilization_time = _value_or(stabilization_time,
                                        self.DEFAULT_STABILIZATION_TIME)
    self.stats = _value_or(stats, self.DEFAULT_STATS)

    total_duration = (
        self.stabilization_time + self.setup_max_duration +
        self.playback_duration + WebPowerStory.DEFAULT_GRACE_PERIOD)
    super().__init__(name_suffix, url, total_duration)

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

  # Toggles the main player UI overlay containing basic interaction buttons
  # (e.g. play/pause, volume, settings cog, fullscreen toggles).
  def _show_controls(self, actions: Actions) -> None:
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
  def run(self, run: Run) -> None:
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

    with run.actions("Media_Playback", verbose=True) as actions:
      actions.wait(self.playback_duration)


class WebPowerMediaPlaybackBenchmark(WebPowerBenchmarkBase):
  """Benchmark runner for Power Media Playback scenario."""

  NAME: ClassVar = f"{WebPowerBenchmarkBase.NAME}-media-playback"
  DEFAULT_STORY_CLS: ClassVar = WebPowerMediaPlaybackStory
  SITE_REQUIRED: ClassVar[bool] = False

  @classmethod
  @override
  def add_cli_arguments(cls, parser: CBArgumentParser) -> CBArgumentParser:
    parser = super().add_cli_arguments(parser)
    story_cls = cls.DEFAULT_STORY_CLS
    default_duration_s = story_cls.DEFAULT_DURATION.total_seconds()
    parser.add_argument(
        "--duration",
        "--playback-duration",
        "--run-for",
        "--stop-after",
        dest="playback_duration",
        type=DurationParser.positive_duration,
        default=story_cls.DEFAULT_DURATION,
        help="How long to play the video for. "
        f"(Default: {default_duration_s:.0f}s)")
    parser.add_argument(
        "--stabilization",
        "--stabilization-time",
        dest="stabilization_time",
        type=DurationParser.positive_or_zero_duration,
        default=story_cls.DEFAULT_STABILIZATION_TIME,
        help="How long to wait after setting up playback to stabilize. "
        f"(Default: "
        f"{story_cls.DEFAULT_STABILIZATION_TIME.total_seconds():.0f}s)")
    parser.add_argument(
        "--stats",
        action="store_true",
        default=story_cls.DEFAULT_STATS,
        help="Enable 'Stats for Nerds' overlay during playback. "
        f"(Default: {str(story_cls.DEFAULT_STATS).lower()})")
    return parser

  @classmethod
  @override
  def kwargs_from_cli(cls, args: argparse.Namespace) -> dict[str, Any]:
    if not args.site and not args.url:
      args.site = "youtube"
    kwargs = super().kwargs_from_cli(args)
    kwargs["playback_duration"] = args.playback_duration
    kwargs["stabilization_time"] = args.stabilization_time
    kwargs["stats"] = args.stats
    return kwargs
