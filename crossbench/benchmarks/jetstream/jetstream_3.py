# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, ClassVar, MutableMapping, Type

from typing_extensions import override

from crossbench.benchmarks.jetstream.jetstream_2 import JetStream2Benchmark, \
    JetStream2Probe, JetStream2ProbeContext, JetStream2Story

if TYPE_CHECKING:
  from crossbench.runner.actions import Actions


# TODO: introduce JetStreamProbe
class JetStream3Probe(JetStream2Probe, metaclass=abc.ABCMeta):
  """
  JetStream3-specific Probe.
  Extracts all JetStream 3 times and scores.
  """


class JetStream3ProbeContext(JetStream2ProbeContext):
  pass


# TODO: introduce JetStreamStory
class JetStream3Story(JetStream2Story, metaclass=abc.ABCMeta):
  SUBSTORIES: ClassVar[tuple[str, ...]] = ()

  @property
  @override
  def url_params(self) -> MutableMapping[str, str]:
    params: MutableMapping[str, str] = super().url_params
    if self.substories != self.SUBSTORIES:
      params["test"] = ",".join(self.substories)
    return params

  @override
  def setup_stories(self, actions: Actions) -> None:
    pass


ProbeClsTupleT = tuple[Type[JetStream3Probe], ...]


# TODO: introduce JetStreamBenchmark
class JetStream3Benchmark(JetStream2Benchmark):
  pass
