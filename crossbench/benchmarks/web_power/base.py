# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
import datetime as dt
import functools
import inspect
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Iterable, Mapping, \
    Self, Sequence, TypeVar, cast

from typing_extensions import override

from crossbench import config
from crossbench import path as pth
from crossbench.benchmarks.base import StoryFilter, SubStoryBenchmark
from crossbench.benchmarks.web_power.wpr_helpers import WprBannerDismisser
from crossbench.cli.config.network import NetworkConfig, NetworkType
from crossbench.helper.path_finder import WprGoFinder
from crossbench.network.replay.wpr import WprReplayNetwork
from crossbench.parse import DurationParser, PathParser
from crossbench.probes.bits import BitsProbe
from crossbench.stories.story import Story

if TYPE_CHECKING:
  import argparse

  from crossbench.action_runner.config import ActionRunnerConfig
  from crossbench.browsers.attributes import BrowserAttributes
  from crossbench.cli.parser import CBArgumentParser
  from crossbench.flags.base import Flags
  from crossbench.path import LocalPath
  from crossbench.plt.base import Platform
  from crossbench.plt.types import ListCmdArgs
  from crossbench.runner.groups.session import BrowserSessionRunGroup
  from crossbench.runner.run import Run
  from crossbench.runner.runner import Runner


_T = TypeVar("_T")
StoryT = TypeVar("StoryT", bound=Story)


# Equivalent to C++'s std::optional::value_or. The Pythonic alternative of
# `value or default` would be thrown off by 0s - hence this helper.
def _value_or(value: _T | None, alternative: _T) -> _T:
  return value if value is not None else alternative


@dataclasses.dataclass(frozen=True)
class WebPowerSiteConfig:
  url: str
  archive: str | None = None


class WebPowerStory(Story):
  DEFAULT_GRACE_PERIOD: ClassVar[dt.timedelta] = dt.timedelta(seconds=20)
  MEASUREMENT_MARK: ClassVar[str] = "web-power"

  IS_SCENARIO_CLASS: ClassVar[bool] = False

  _scenario_classes: ClassVar[list[type[WebPowerStory]]] = []

  def __init_subclass__(cls, **kwargs) -> None:
    super().__init_subclass__(**kwargs)
    if cls.IS_SCENARIO_CLASS:
      WebPowerStory._scenario_classes.append(cls)

  @classmethod
  def scenario_classes(cls) -> tuple[type[WebPowerStory], ...]:
    return tuple(cls._scenario_classes)

  _LEGACY_WPR_RECORDING = ("gs://chrome-partner-loadline/power/"
                           "CHROME_EFFICIENCY_KPI_2026_04_03.wprgo")

  _CANONICAL_SITES: ClassVar[dict[str, WebPowerSiteConfig]] = {
      "ajnews":
          WebPowerSiteConfig(
              url="https://aljazeera.com",
              archive=_LEGACY_WPR_RECORDING,
          ),
      "cnn":
          WebPowerSiteConfig(
              url="https://www.cnn.com",
              archive=("gs://chrome-partner-loadline/power/cnn_20260513.wprgo"),
          ),
      "msn":
          WebPowerSiteConfig(
              url="https://msn.com/en-us",
              archive=_LEGACY_WPR_RECORDING,
          ),
      "youtube":
          WebPowerSiteConfig(
              url="https://www.youtube.com/watch?v=XITHbsUUlYI",
              archive=("gs://chrome-partner-loadline/power/"
                       "youtube_2026_05_18.wprgo"),
          ),
  }

  _NON_CANONICAL_SITES: ClassVar[dict[str, WebPowerSiteConfig]] = {
      "yahoo":
          WebPowerSiteConfig(
              url="https://www.yahoo.com",
              archive=_LEGACY_WPR_RECORDING,
          ),
  }

  SITES: ClassVar[dict[str, WebPowerSiteConfig]] = {
      **_CANONICAL_SITES,
      **_NON_CANONICAL_SITES,
  }

  @classmethod
  def from_site(cls, site_key: str, *args: Any, **kwargs: Any) -> Self:
    if site_key not in cls.SITES:
      raise ValueError(f"Unknown web power benchmark site key: {site_key}")
    return cls(site_key, cls.SITES[site_key], *args, **kwargs)

  @classmethod
  def from_url(cls, url: str, *args: Any, **kwargs: Any) -> Self:
    return cls("custom", WebPowerSiteConfig(url=url), *args, **kwargs)

  def __init__(self, name_suffix: str, site_config: WebPowerSiteConfig,
               total_duration: dt.timedelta) -> None:
    self.site_config = site_config
    super().__init__(
        f"web-power-{self.story_name}-{name_suffix}", total_duration)

  @property
  def url(self) -> str:
    return self.site_config.url

  @classmethod
  def story_name_cls(cls) -> str:
    raise NotImplementedError("Subclasses must implement story_name_cls")

  @property
  def story_name(self) -> str:
    return self.story_name_cls()

  @override
  def run(self, run: Run) -> None:
    raise NotImplementedError

  @classmethod
  def default_story_names(cls) -> tuple[str, ...]:
    if cls is not WebPowerStory:
      # TODO(eladalon): Derive this more nicely without picking up YouTube,
      # which we don't use for anything other than media-playback.
      return ("msn", "cnn", "ajnews")
    return cls.all_story_names()

  @classmethod
  @functools.cache
  def all_story_names(cls) -> tuple[str, ...]:
    if cls is not WebPowerStory:
      return tuple(sorted(cls.SITES.keys()))
    names: list[str] = []
    for story_cls in cls.scenario_classes():
      scenario = story_cls.story_name_cls()
      for site in story_cls.default_story_names():
        names.append(f"{scenario}-{site}")
    return tuple(sorted(names))

  @classmethod
  @functools.cache
  @override
  def all_tags_lookup(cls) -> Mapping[str, Iterable[str]]:
    """Returns a lookup dictionary mapping story names to their tags.

    Example return value:
    {
        "idle-msn": ["idle", "msn", "canonical"],
        "media-playback-youtube": ["media-playback", "youtube"],
    }
    """
    if cls is not WebPowerStory:
      return super().all_tags_lookup()
    lookup: dict[str, list[str]] = {}
    for name in cls.all_story_names():
      scenario, site = name.rsplit("-", 1)
      lookup[name] = [scenario, site]
      if site in cls._CANONICAL_SITES:
        lookup[name].append("canonical")
    return lookup


WebPowerStoryT = TypeVar("WebPowerStoryT", bound=WebPowerStory)


class WebPowerStoryFilter(StoryFilter[WebPowerStoryT], Generic[WebPowerStoryT]):
  """Base story filter for Web Power benchmarks."""

  STORY_CLS: ClassVar[type[WebPowerStory]] = WebPowerStory  # type: ignore

  IS_SCENARIO_CLASS: ClassVar[bool] = False

  _scenario_filters: ClassVar[list[type[WebPowerStoryFilter]]] = []

  def __init_subclass__(cls, **kwargs) -> None:
    super().__init_subclass__(**kwargs)
    if cls.IS_SCENARIO_CLASS:
      WebPowerStoryFilter._scenario_filters.append(cls)

  @classmethod
  def scenario_filters(cls) -> tuple[type[WebPowerStoryFilter], ...]:
    return tuple(cls._scenario_filters)

  def __init__(
      self,
      story_cls: type[WebPowerStoryT],
      patterns: Sequence[str],
      args: argparse.Namespace,
      separate: bool = True,
      tags: Iterable[str] = (),
      **story_kwargs: Any,
  ) -> None:
    self._story_kwargs = story_kwargs
    super().__init__(story_cls, patterns, args, separate, tags)

  @classmethod
  @override
  def kwargs_from_cli(cls, args: argparse.Namespace) -> dict[str, Any]:
    kwargs = super().kwargs_from_cli(args)
    kwargs.update(vars(args))
    return kwargs

  @classmethod
  @override
  def add_cli_arguments(
      cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser = super().add_cli_arguments(parser)
    parser.set_defaults(separate=True)
    return parser

  @classmethod
  @override
  def _add_story_filtering_arguments(
      cls, group: argparse._MutuallyExclusiveGroup) -> None:
    super()._add_story_filtering_arguments(group)
    group.add_argument(
        "--site",
        choices=cls.STORY_CLS.all_story_names(),
        help="Specific pre-recorded site to run (from a closed list).",
    )
    group.add_argument("--url", help="Custom URL to run.")

  @override
  def stories_from_names(self,
                         names: Sequence[str]) -> tuple[WebPowerStoryT, ...]:
    return tuple(
        self._instantiate_story(self.story_cls, name) for name in names)

  def _instantiate_story(self, story_cls: type[WebPowerStoryT],
                         site_name: str) -> WebPowerStoryT:
    """Instantiates a story class with site-specific configurations.

    Filters all parsed CLI arguments to only forward parameters accepted by the
    target story constructor (preventing TypeErrors).

    This means that we can run `./cb.py web-power --stories=#cnn` and specify
    `--scrolls` to affect the scroll-cnn story, without it raising an error for
    the stories where it's not relevant, such as idle-cnn.
    """
    constructor_sig = inspect.signature(story_cls.__init__)
    accepted_params = constructor_sig.parameters

    filtered_kwargs = {}
    for key in self._story_kwargs:
      if key not in accepted_params:
        continue
      value = self._story_kwargs[key]
      if value is not None:
        filtered_kwargs[key] = value

    return story_cls.from_site(site_name, **filtered_kwargs)


class WebPowerBenchmarkBase(SubStoryBenchmark):
  """Base class for Power benchmarks to share common logic."""

  IS_SCENARIO_CLASS: ClassVar[bool] = False

  _scenario_benchmarks: ClassVar[list[type[WebPowerBenchmarkBase]]] = []

  def __init_subclass__(cls, **kwargs) -> None:
    super().__init_subclass__(**kwargs)
    if cls.IS_SCENARIO_CLASS:
      WebPowerBenchmarkBase._scenario_benchmarks.append(cls)

  @classmethod
  def scenario_benchmarks(cls) -> tuple[type[WebPowerBenchmarkBase], ...]:
    return tuple(cls._scenario_benchmarks)

  @classmethod
  def add_scenario_cli_arguments(cls,
                                 parser: CBArgumentParser) -> CBArgumentParser:
    raise NotImplementedError

  NAME: ClassVar = "web-power"
  DEFAULT_REPETITIONS: ClassVar[int] = 5
  DEFAULT_COOL_DOWN: ClassVar[dt.timedelta] = dt.timedelta(minutes=2)
  SITE_REQUIRED: ClassVar[bool] = True
  REQUIRES_AUTOPLAY: ClassVar[bool] = False
  STORY_FILTER_CLS: ClassVar[type[StoryFilter]] = WebPowerStoryFilter
  DEFAULT_STORY_CLS: ClassVar[type[WebPowerStory]]

  def __init__(
      self,
      stories: Sequence[WebPowerStory],
      action_runner_config: ActionRunnerConfig | None = None,
      bits_probe: BitsProbe | None = None,
  ) -> None:
    self._bits_probe = bits_probe
    super().__init__(stories, action_runner_config)

  @override
  def _validate_stories(self, stories: Sequence[Story]) -> list[Story]:
    assert stories, "No stories provided"
    assert all(isinstance(story, WebPowerStory) for story in stories)
    return list(stories)

  @classmethod
  @override
  def stories_from_cli_args(cls, args: argparse.Namespace) -> Sequence[Story]:
    if args.url:
      filter_kwargs = cls.STORY_FILTER_CLS.kwargs_from_cli(args)
      story_kwargs = filter_kwargs.get("story_kwargs", {})
      return [cls.DEFAULT_STORY_CLS.from_url(args.url, **story_kwargs)]
    if args.site:
      args.stories = args.site
    return super().stories_from_cli_args(args)

  @override
  def setup(self, runner: Runner) -> None:
    super().setup(runner)
    if self._bits_probe:
      runner.attach_probe(self._bits_probe)

  @override
  def setup_session_network(self, session: BrowserSessionRunGroup) -> None:
    super().setup_session_network(session)
    assert session.is_single_run
    story = session.first_run.story
    assert isinstance(story, WebPowerStory)

    network = session.network
    if not isinstance(network, WprReplayNetwork):
      return

    if story.site_config.archive:
      local_archive_path = network.ensure_archive(story.site_config.archive)
      network.set_archive_path(local_archive_path)

    if network.archive_path:
      httparchive_path = WprGoFinder(session.host_platform).httparchive()
      self._setup_single_wpr_transformation(session.host_platform, network,
                                            httparchive_path)

  def _setup_single_wpr_transformation(
      self,
      host_platform: Platform,
      network: WprReplayNetwork,
      httparchive_path: LocalPath,
  ) -> None:
    args: ListCmdArgs = [
        httparchive_path, "read-metadata", network.archive_path
    ]
    metadata = host_platform.sh_stdout(*args)
    if res := WprBannerDismisser.create_rules(metadata):
      js_payload, target_url = res
      rules_file = WprBannerDismisser.serialize_rules(js_payload, target_url)
      network.set_response_transformations_file(rules_file)


  @classmethod
  @override
  def extra_flags(cls, browser_attributes: BrowserAttributes) -> Flags:
    flags: Flags = super().extra_flags(browser_attributes)
    if browser_attributes.is_chromium_based:
      if cls.REQUIRES_AUTOPLAY:
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
    parser = cast("CBArgumentParser",
                  cls.STORY_FILTER_CLS.add_cli_arguments(parser))
    parser.add_argument(
        "--bits-path",
        type=PathParser.existing_file_path,
        help="Path to the BITS external tool binary on the host.",
    )
    parser.add_argument(
        "--bits-out",
        help="Output identifier for the BITS tool.",
    )
    parser.add_argument(
        "--bits-device",
        default="",
        help="Device identifier for the BITS tool.",
    )
    parser.add_argument(
        "--bits-duration",
        type=DurationParser.positive_duration,
        default=BitsProbe.DEFAULT_DURATION,
        help="Duration for the BITS tool to run.",
    )
    if cls.IS_SCENARIO_CLASS:
      return cls.add_scenario_cli_arguments(parser)
    return parser

  @classmethod
  @override
  def kwargs_from_cli(cls, args: argparse.Namespace) -> dict[str, Any]:
    kwargs = super().kwargs_from_cli(args)
    cls._select_network(args)
    if args.bits_path or args.bits_out:
      kwargs["bits_probe"] = BitsProbe.parse_dict({
          "path": args.bits_path,
          "out": args.bits_out,
          "device": args.bits_device,
          "duration": args.bits_duration,
      })
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
    if network and network.type == NetworkType.WPR:
      args.network = dataclasses.replace(network, no_archive_certificates=True)

  @classmethod
  def _setup_pre_recorded_site_network(cls, args: argparse.Namespace) -> None:
    # This code executes once, before the first story, so choosing the
    # first story is fine.
    site = _value_or(args.site, cls.DEFAULT_STORY_CLS.default_story_names()[0])
    site_key = site
    # TODO(eladalon): Get subclasses to register themselves and derive this
    # list of scenarios from that.
    for scenario in ("idle", "scroll", "page-load", "media-playback"):
      prefix = f"{scenario}-"
      if site.startswith(prefix):
        site_key = site[len(prefix):]
        break
    story_cls = cls.DEFAULT_STORY_CLS
    site_config = story_cls.SITES.get(site_key)
    if not site_config or not site_config.archive:
      raise ValueError(
          "Web Power benchmarks require an explicit, known '--site' "
          f"or '--story' to use a mapped WPR recording. Got: {site}")
    args.network = NetworkConfig(
        type=NetworkType.WPR,
        url=site_config.archive,
        no_archive_certificates=True)

  @classmethod
  @override
  def default_probe_config_path(cls) -> pth.LocalPath | None:
    return (config.config_dir() / "benchmark/web_power/probe_config.hjson")
