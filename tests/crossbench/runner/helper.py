# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import abc
import json
import pathlib
from typing import Any, List, Optional

from crossbench.browsers.browser import Browser
from crossbench.env import HostEnvironment
from crossbench.path import safe_filename
from crossbench.probes.probe import Probe, ProbeContext
from crossbench.probes.probe_context import ProbeContext
from crossbench.probes.results import LocalProbeResult, ProbeResult
from crossbench.runner.run import Run
from crossbench.runner.runner import Runner
from crossbench.runner.timing import Timing
from tests.crossbench.mock_browser import MockChromeDev, MockFirefox
from tests.crossbench.mock_helper import (BaseCrossbenchTestCase,
                                          MockBenchmark, MockStory)


class MockBrowser:

  def __init__(self, unique_name: str, platform) -> None:
    self.unique_name = unique_name
    self.platform = platform
    self.network = MockNetwork()

  def __str__(self):
    return self.unique_name


class MockRun:

  def __init__(self, runner, browser_session, name) -> None:
    self.runner = runner
    self.browser_session = browser_session
    self.browser = browser_session.browser
    self.browser_platform = self.browser.platform
    self.name = name
    self.probes = []
    self.timing = Timing()
    self.is_success = True
    self.out_dir = (
        browser_session.root_dir / safe_filename(self.browser.unique_name) /
        "stories" / name / "repetition=0" / "temperature-cold")

  def validate_env(self, env: HostEnvironment):
    pass

  def __str__(self):
    return self.name


class MockPlatform:

  def __init__(self, name) -> None:
    self.name = name

  def __str__(self):
    return self.name


class MockRunner:

  def __init__(self) -> None:
    self.runs = tuple()


class MockNetwork:
  pass


class MockProbe(Probe):
  NAME = "test-probe"

  def __init__(self, test_data: Any = ()) -> None:
    super().__init__()
    self.test_data = test_data

  @property
  def result_path_name(self) -> str:
    return f"{self.name}.json"

  def get_context(self, run: Run):
    return MockProbeContext(self, run)


class MockProbeContext(ProbeContext):

  def start(self) -> None:
    pass

  def stop(self) -> None:
    pass

  def teardown(self) -> ProbeResult:
    with self.result_path.open("w") as f:
      json.dump(self.probe.test_data, f)
    return LocalProbeResult(json=(self.result_path,))


class BaseRunnerTestCase(BaseCrossbenchTestCase, metaclass=abc.ABCMeta):

  def setUp(self):
    super().setUp()
    self.out_dir = pathlib.Path("testing/out_dir")
    self.out_dir.parent.mkdir(exist_ok=False, parents=True)
    self.stories = [MockStory("story_1"), MockStory("story_2")]
    self.benchmark = MockBenchmark(self.stories)
    self.browsers: List[Browser] = [
        MockChromeDev("chrome-dev", platform=self.platform),
        MockFirefox("firefox-stable", platform=self.platform)
    ]

  def default_runner(self,
                     browsers: Optional[List[Browser]] = None,
                     throw: bool = True) -> Runner:
    if browsers is None:
      browsers = self.browsers
    return Runner(
        self.out_dir,
        browsers,
        self.benchmark,
        platform=self.platform,
        throw=throw)
