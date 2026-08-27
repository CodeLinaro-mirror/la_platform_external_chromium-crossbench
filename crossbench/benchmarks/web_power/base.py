# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import dataclasses
import datetime as dt
import functools
import inspect
from typing import TYPE_CHECKING, Any, ClassVar, Final, Generic, Iterable, \
    Mapping, Self, Sequence, TypeVar, cast

from typing_extensions import override

from crossbench.action_runner.action.enums import WindowTarget
from crossbench.benchmarks.base import StoryFilter, SubStoryBenchmark
from crossbench.benchmarks.web_power.probe import WebPowerProbe
from crossbench.benchmarks.web_power.wpr_helpers import WprBannerDismisser
from crossbench.cli.config.network import NetworkConfig, NetworkType
from crossbench.helper.path_finder import WprGoFinder
from crossbench.network.replay.wpr import WprReplayNetwork
from crossbench.parse import DurationParser, PathParser
from crossbench.probes.bits import BitsProbe
from crossbench.probes.junction_temperature import \
    JunctionTemperatureProbe as JtProbe
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

# The Web Power benchmarks will follow an `a.b.c` scheme, where:
# - The A portion of a.b.c refers to the year, with year one being 2026.
# - The B portion of a.b.c refers to the major revision within the year.
#   This is incremented with major, score-affecting changes to the workloads.
# - The C portion of a.b.c refers to minor, score-unaffecting changes; e.g.
#   "quality of life" improvements, changes to the cool-off period determined
#   not to affect thermals, etc.
VERSION_STRING: Final[str] = "1.1.5"

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
  default_stabilization_time: dt.timedelta = dt.timedelta(seconds=10)


class WebPowerStory(Story):
  DEFAULT_GRACE_PERIOD: ClassVar[dt.timedelta] = dt.timedelta(seconds=20)
  MEASUREMENT_MARK: ClassVar[str] = "web-power"

  IS_SCENARIO_CLASS: ClassVar[bool] = False
  REQUIRES_AUTOPLAY: ClassVar[bool] = False
  WINDOW_TARGET: ClassVar[WindowTarget] = WindowTarget.SELF

  _scenario_classes: ClassVar[list[type[WebPowerStory]]] = []

  def __init_subclass__(cls, **kwargs) -> None:
    super().__init_subclass__(**kwargs)
    if cls.IS_SCENARIO_CLASS:
      WebPowerStory._scenario_classes.append(cls)

  @classmethod
  def scenario_classes(cls) -> tuple[type[WebPowerStory], ...]:
    return tuple(cls._scenario_classes)

  _WEB_POWER_GCS = "gs://chrome-partner-loadline/power"
  _LEGACY_WPR_RECORDING = (
      f"{_WEB_POWER_GCS}/CHROME_EFFICIENCY_KPI_2026_04_03.wprgo")

  _CANONICAL_SITES: ClassVar[dict[str, WebPowerSiteConfig]] = {
      "ajnews":
          WebPowerSiteConfig(
              url="https://aljazeera.com",
              archive=_LEGACY_WPR_RECORDING,
          ),
      "cnn":
          WebPowerSiteConfig(
              url="https://www.cnn.com",
              archive=f"{_WEB_POWER_GCS}/cnn_20260513.wprgo",
          ),
      "msn":
          WebPowerSiteConfig(
              url="https://msn.com/en-us",
              archive=_LEGACY_WPR_RECORDING,
              default_stabilization_time=dt.timedelta(seconds=60),
          ),
      "youtube":
          WebPowerSiteConfig(
              url="https://www.youtube.com/watch?v=XITHbsUUlYI",
              archive=f"{_WEB_POWER_GCS}/youtube_2026_05_18.wprgo",
          ),
  }

  _NON_CANONICAL_SITES: ClassVar[dict[str, WebPowerSiteConfig]] = {
      "allrecipes":
          WebPowerSiteConfig(
              url="https://www.allrecipes.com",
              archive=f"{_WEB_POWER_GCS}/allrecipes_2026_08_20.wprgo",
          ),
      "telegraph":
          WebPowerSiteConfig(
              url="https://www.telegraph.co.uk",
              archive=f"{_WEB_POWER_GCS}/telegraph_2026_08_20.wprgo",
          ),
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
               total_duration: dt.timedelta,
               stabilization_time: dt.timedelta) -> None:
    self.site_config = site_config
    self.stabilization_time = stabilization_time
    super().__init__(f"web-power-{self.story_name}-{name_suffix}",
                     total_duration)

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
  def setup(self, run: Run) -> None:
    with run.actions("Show URL", verbose=True) as actions:
      actions.show_url(self.url, target=self.WINDOW_TARGET)
    if self.stabilization_time.total_seconds() > 0:
      with run.actions("Stabilization", verbose=True) as actions:
        actions.wait(self.stabilization_time)

  @override
  def run(self, run: Run) -> None:
    raise NotImplementedError

  @classmethod
  @override
  def default_story_names(cls) -> tuple[str, ...]:
    return tuple(name for name in cls.all_story_names()
                 if name.rsplit("-", 1)[-1] in cls._CANONICAL_SITES)

  @classmethod
  @override
  def all_story_names(cls) -> tuple[str, ...]:
    if cls is not WebPowerStory:
      return tuple(sorted(site for site in cls.SITES if site != "youtube"))
    names: list[str] = []
    for story_cls in cls.scenario_classes():
      scenario = story_cls.story_name_cls()
      for site in story_cls.all_story_names():
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
      lookup[name] = [site]
      if site in cls._CANONICAL_SITES:
        lookup[name].extend([scenario, "canonical"])
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

  @classmethod
  def fast_mode_default_overrides(cls) -> dict[str, Any]:
    overrides = super().fast_mode_default_overrides()
    overrides["duration"] = dt.timedelta(seconds=3)
    overrides["repetitions"] = 1
    overrides["stabilization_time"] = dt.timedelta(seconds=3)
    return overrides

  NAME: ClassVar = "web-power"
  DEFAULT_REPETITIONS: ClassVar[int] = 5
  DEFAULT_COOL_DOWN: ClassVar[dt.timedelta] = dt.timedelta(minutes=2)
  SITE_REQUIRED: ClassVar[bool] = True
  STORY_FILTER_CLS: ClassVar[type[StoryFilter]] = WebPowerStoryFilter
  DEFAULT_STORY_CLS: ClassVar[type[WebPowerStory]]
  PROBES: ClassVar = (WebPowerProbe,)

  def __init__(
      self,
      stories: Sequence[WebPowerStory],
      action_runner_config: ActionRunnerConfig | None = None,
      bits_probe: BitsProbe | None = None,
  ) -> None:
    self._bits_probe = bits_probe
    super().__init__(stories, action_runner_config)

  @property
  def bits_probe(self) -> BitsProbe | None:
    return self._bits_probe

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
    # TODO: Move JtProbe attachment to WebPowerProbe.get_extra_probes().
    if not runner.has_probe(JtProbe.NAME):
      runner.attach_probe(JtProbe(), matching_browser_only=True)

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
  def extra_flags(cls, browser_attributes: BrowserAttributes,
                  story: Story) -> Flags:
    flags: Flags = super().extra_flags(browser_attributes, story)
    if browser_attributes.is_chromium_based:
      assert isinstance(story, WebPowerStory)
      if story.REQUIRES_AUTOPLAY:
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
          "--disable-notifications",
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
        "--benchmark-version", action="version", version=f"{VERSION_STRING}")
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
    parser.add_argument(
        "--bits-port",
        type=int,
        default=None,
        help="Port for the BITS tool to use.",
    )
    parser.add_argument(
        "--stabilization",
        "--stabilization-time",
        dest="stabilization_time",
        type=DurationParser.positive_or_zero_duration,
        help=("How long to wait to stabilize after loading the page, "
              "but before the story run starts."),
    )
    if cls.IS_SCENARIO_CLASS:
      return cls.add_scenario_cli_arguments(parser)
    return parser

  @classmethod
  @override
  def kwargs_from_cli(cls, args: argparse.Namespace) -> dict[str, Any]:
    kwargs = super().kwargs_from_cli(args)
    cls._select_network(args)
    if bits_probe := cls._parse_bits_probe(args):
      kwargs["bits_probe"] = bits_probe
    return kwargs

  @classmethod
  def _parse_bits_probe(cls, args: argparse.Namespace) -> BitsProbe | None:
    if not args.bits_path and not args.bits_out:
      return None
    return BitsProbe.parse_dict({
        "path": args.bits_path,
        "out": args.bits_out,
        "device": args.bits_device,
        "duration": args.bits_duration,
        "port": args.bits_port,
    })

  @classmethod
  def _select_network(cls, args: argparse.Namespace) -> None:
    network: NetworkConfig = args.network_config
    if network and not network.is_default():
      cls._setup_explicit_network(args, network)
    elif not args.url:
      cls._setup_pre_recorded_site_network(args)

  @classmethod
  def _setup_explicit_network(cls, args: argparse.Namespace,
                              network: NetworkConfig) -> None:
    if args.site:
      raise ValueError(
          "Specifying '--site' is mutually exclusive with explicit "
          "'--network' or '--wpr' flags, as it implies the selection "
          "of a specific WPR recording. Explicit networks are only "
          "supported when testing with '--url'.")
    if network.type == NetworkType.WPR:
      args.network_config = dataclasses.replace(
          network, no_archive_certificates=True)

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
    args.network_config = NetworkConfig(
        type=NetworkType.WPR,
        url=site_config.archive,
        no_archive_certificates=True)
