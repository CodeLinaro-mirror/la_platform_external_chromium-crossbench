# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
from typing import TYPE_CHECKING, Any, ClassVar, Self, Sequence, TypeVar

from typing_extensions import override

from crossbench.benchmarks.base import Benchmark
from crossbench.cli.config.network import NetworkConfig, NetworkType
from crossbench.stories.story import Story

if TYPE_CHECKING:
  from crossbench.action_runner.config import ActionRunnerConfig
  from crossbench.browsers.attributes import BrowserAttributes
  from crossbench.cli.parser import CBArgumentParser
  from crossbench.flags.base import Flags


_T = TypeVar("_T")


# Equivalent to C++'s std::optional::value_or. The Pythonic alternative of
# `value or default` would be thrown off by 0s - hence this helper.
def _value_or(value: _T | None, alternative: _T) -> _T:
  return value if value is not None else alternative


class PowerStory(Story):
  DEFAULT_GRACE_PERIOD: ClassVar[dt.timedelta] = dt.timedelta(seconds=20)

  _LEGACY_WPR_RECORDING = ("gs://chrome-partner-loadline/power/"
                           "CHROME_EFFICIENCY_KPI_2026_04_03.wprgo")

  _CANONICAL_SITES: ClassVar[dict[str, dict[str, str]]] = {
      "ajnews": {
          "url": "https://aljazeera.com",
          "archive": _LEGACY_WPR_RECORDING,
      },
      "cnn": {
          "url": "https://www.cnn.com",
          "archive": "gs://chrome-partner-loadline/power/cnn_20260513.wprgo",
      },
      "msn": {
          "url": "https://msn.com/en-us",
          "archive": _LEGACY_WPR_RECORDING,
      },
      "youtube": {
          "url":
              "https://www.youtube.com/watch?v=XITHbsUUlYI",
          "archive":
              "gs://chrome-partner-loadline/power/youtube_2026_05_18.wprgo",
      },
  }

  _NON_CANONICAL_SITES: ClassVar[dict[str, dict[str, str]]] = {
      "yahoo": {
          "url": "https://www.yahoo.com",
          "archive": _LEGACY_WPR_RECORDING,
      },
  }

  SITES: ClassVar[dict[str, dict[str, str]]] = {
      **_CANONICAL_SITES,
      **_NON_CANONICAL_SITES,
  }

  @classmethod
  def from_site(cls, site_key: str, *args: Any, **kwargs: Any) -> Self:
    site_config = cls.SITES.get(site_key, {})
    url = site_config.get("url", "")
    if not url:
      raise ValueError(f"Unknown power benchmark site key: {site_key}")
    return cls(site_key, url, *args, **kwargs)

  @classmethod
  def from_url(cls, url: str, *args: Any, **kwargs: Any) -> Self:
    return cls("custom", url, *args, **kwargs)

  def __init__(self, name_suffix: str, url: str,
               total_duration: dt.timedelta) -> None:
    self.url = url
    super().__init__(f"power-{self.story_name}-{name_suffix}", total_duration)

  @property
  def story_name(self) -> str:
    raise NotImplementedError("Subclasses must implement story_name")

  @classmethod
  def all_story_names(cls) -> Sequence[str]:
    return sorted(cls.SITES.keys())


class PowerBenchmarkBase(Benchmark):
  """Base class for Power benchmarks to share common logic."""

  NAME: ClassVar = "power"  # Subclasses expected to extend to "power-xyz"
  SITE_REQUIRED: ClassVar[bool] = True

  def __init__(
      self,
      action_runner_config: ActionRunnerConfig | None = None,
      site_key: str | None = None,
      url: str | None = None,
      **story_kwargs: Any,
  ) -> None:
    story_cls = getattr(self.__class__, "DEFAULT_STORY_CLS", None)
    assert story_cls is not None
    if url:
      stories = [story_cls.from_url(url, **story_kwargs)]
    else:
      stories = [story_cls.from_site(site_key or "", **story_kwargs)]
    super().__init__(stories, action_runner_config)

  @classmethod
  @override
  def extra_flags(cls, browser_attributes: BrowserAttributes) -> Flags:
    flags: Flags = super().extra_flags(browser_attributes)
    if browser_attributes.is_chromium_based:
      flags.set("--autoplay-policy", "no-user-gesture-required")
      flags.set("--remote-allow-origins", "*")
      for flag in (
          "--disable-background-timer-throttling",
          "--disable-component-update",
          "--disable-external-intent-requests",
          "--disable-optimization-guide-model-downloads-for-benchmarking",
          "--disable-renderer-backgrounding",
          "--disable-stack-profiler",
          "--disable-gesture-requirement-for-presentation",
      ):
        flags.set(flag)
    return flags

  @classmethod
  @override
  def add_cli_arguments(cls, parser: CBArgumentParser) -> CBArgumentParser:
    parser = super().add_cli_arguments(parser)
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--site",
        choices=cls.DEFAULT_STORY_CLS.all_story_names(),
        help="Specific pre-recorded site to run (from a closed list).",
    )
    group.add_argument("--url", help="Custom URL to run.")
    return parser

  @classmethod
  @override
  def kwargs_from_cli(cls, args: argparse.Namespace) -> dict[str, Any]:
    if cls.SITE_REQUIRED and not args.site and not args.url:
      raise argparse.ArgumentTypeError(
          "One of the arguments --site --url is required")
    kwargs = super().kwargs_from_cli(args)
    cls._select_network(args)
    kwargs["site_key"] = args.site
    kwargs["url"] = args.url
    return kwargs

  @classmethod
  def _select_network(cls, args: argparse.Namespace) -> None:
    if getattr(args, "has_explicit_network", False):
      cls._setup_explicit_network(args)
    elif not args.url:
      cls._setup_pre_recorded_site_network(args)

  @classmethod
  def _setup_explicit_network(cls, args: argparse.Namespace) -> None:
    if args.site:
      raise ValueError(
          "Specifying '--site' is mutually exclusive with explicit "
          "'--network' or '--wpr' flags, as it implies the selection "
          "of a specific WPR recording. Explicit networks are only "
          "supported when testing with '--url'.")
    network = getattr(args, "network", None)
    if network and getattr(network, "type", None) == NetworkType.WPR:
      args.network = dataclasses.replace(network, no_archive_certificates=True)

  @classmethod
  def _setup_pre_recorded_site_network(cls, args: argparse.Namespace) -> None:
    story_cls = cls.DEFAULT_STORY_CLS
    site_config = getattr(story_cls, "SITES", {}).get(args.site, {})
    wpr_url = site_config.get("archive")
    if not wpr_url:
      raise ValueError(
          f"Power benchmarks require an explicit, known '--site' to use a "
          f"mapped WPR recording. Got: {args.site}")
    args.network = NetworkConfig(
        type=NetworkType.WPR, url=wpr_url, no_archive_certificates=True)
