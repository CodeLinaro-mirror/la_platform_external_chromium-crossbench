# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, ClassVar, Mapping, Sequence

from typing_extensions import Self, override

from crossbench.benchmarks.jetstream.jetstream_2 import JetStream2Benchmark, \
    JetStream2BenchmarkStoryFilter, JetStream2Probe, JetStream2ProbeContext, \
    JetStream2Story
from crossbench.helper import url_helper

if TYPE_CHECKING:
  import argparse

  from crossbench.runner.actions import Actions
  from crossbench.types import StoryTagLookupT


# TODO: introduce JetStreamProbe
class JetStream3Probe(JetStream2Probe, metaclass=abc.ABCMeta):
  """
  JetStream3-specific Probe.
  Extracts all JetStream 3 times and scores.
  """


class JetStream3ProbeContext(JetStream2ProbeContext):
  JS: ClassVar[str] = "return JetStream.resultsJSON('simple');"

  @override
  def to_json(self, actions: Actions) -> dict[str, float]:
    result = super().to_json(actions)
    lowercase_results = {}

    for key, value in result.items():
      lowercase_results[key.lower()] = value

    return lowercase_results


# TODO: introduce JetStreamStory
class JetStream3Story(JetStream2Story, metaclass=abc.ABCMeta):
  STORY_DATA: ClassVar[Mapping[str, tuple[str, ...]]]

  @classmethod
  def all_tags_lookup(cls) -> StoryTagLookupT:
    return cls.STORY_DATA

  @classmethod
  @override
  def default_story_names(cls) -> tuple[str, ...]:
    return tuple(
        name for name, tags in cls.STORY_DATA.items() if "default" in tags)

  @classmethod
  @override
  def from_names(cls,
                 substories: Sequence[str],
                 separate: bool = False,
                 url: str | None = None,
                 **kwargs) -> tuple[Self, ...]:
    if not substories:
      raise ValueError("No substories provided")
    if separate:
      return tuple(
          cls(url=url,
              substories=[substory],
              tags=cls.STORY_DATA.get(substory, ()),
              **kwargs) for substory in substories)
    tags: set[str] = set()
    for substory in substories:
      tags.update(cls.STORY_DATA.get(substory, ()))
    return (cls(url=url, substories=substories, tags=tags, **kwargs),)

  @property
  @override
  def url_params(self) -> dict[str, str]:
    params: dict[str, str] = super().url_params
    if self.substories != self.default_story_names():
      params["test"] = ",".join(self.substories)
    return params

  @property
  @override
  def test_url(self) -> str:
    params: dict[str, str] = self.url_params
    params["developerMode"] = ""
    params["startAutomatically"] = ""
    official_test_url = url_helper.update_url_query(self.URL, params)
    return official_test_url

  @override
  def setup_stories(self, actions: Actions) -> None:
    pass


ProbeClsTupleT = tuple[type[JetStream3Probe], ...]


class JetStream3BenchmarkStoryFilter(JetStream2BenchmarkStoryFilter):
  __doc__ = JetStream2BenchmarkStoryFilter.__doc__

  @classmethod
  @override
  def add_cli_arguments(
      cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser = super().add_cli_arguments(parser)
    parser.add_argument(
        "--no-prefetch",
        dest="prefetch_resources",
        default=True,
        action="store_false",
        help=("Disable resources prefetching for better source positions. "
              "This might skew results as we do network request on the hot"
              "path"))
    return parser

  @classmethod
  def url_params_from_cli(cls, args: argparse.Namespace) -> dict[str, str]:
    url_params: dict[str, str] = super().url_params_from_cli(args)
    if not args.prefetch_resources:
      url_params["prefetchResources"] = "false"
    return url_params


# TODO: introduce JetStreamBenchmark
class JetStream3Benchmark(JetStream2Benchmark):
  STORY_FILTER_CLS: ClassVar = JetStream3BenchmarkStoryFilter
  DEFAULT_STORY_CLS: ClassVar[type[JetStream3Story]]
