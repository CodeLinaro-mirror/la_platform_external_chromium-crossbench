# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from typing import Iterable, Mapping, MutableMapping, Sequence

from immutabledict import immutabledict

type Json = JsonMapping | JsonSequence | str | int | float | bool | None
type JsonMapping = Mapping[str, Json]
type JsonMutableMapping = MutableMapping[str, Json]
type JsonDict = dict[str, Json]
type ImmutableJsonDict = immutabledict[str, Json]
type JsonSequence = Sequence[Json]
type JsonList = list[Json]
type JsonTuple = tuple[Json, ...]
type StoryTagLookupT = Mapping[str, Iterable[str]]
type TableData = list[list[str]]
