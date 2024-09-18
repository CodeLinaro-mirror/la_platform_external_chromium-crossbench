# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import abc
import datetime as dt
import json
import pathlib
from typing import Any, List, Optional

from crossbench.browsers.browser import Browser
from crossbench.browsers.settings import Settings
from crossbench.env import HostEnvironment
from crossbench.exception import Annotator
from crossbench.path import safe_filename
from crossbench.probes.probe import Probe, ProbeContext
from crossbench.probes.probe_context import ProbeContext
from crossbench.probes.results import LocalProbeResult, ProbeResult
from crossbench.runner.actions import Actions
from crossbench.runner.run import Run
from crossbench.runner.runner import Runner
from crossbench.runner.timing import Timing
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.mock_browser import MockChromeDev, MockFirefox
from tests.crossbench.mock_helper import MockBenchmark, MockStory


class MockBrowser:

  def __init__(self, unique_name: str, platform) -> None:
    self.unique_name = unique_name
    self.platform = platform
    self.network = MockNetwork()

  def __str__(self):
    return self.unique_name


class MockRun:

  def __init__(self,
               runner,
               browser_session,
               story="story",
               repetition=0,
               is_warmup=False,
               temperature="default",
               index=0,
               name="run 0") -> None:
    self.runner = runner
    self.browser_session = browser_session
    self.browser = browser_session.browser
    self.browser_platform = self.browser.platform
    self._exceptions = Annotator(False)
    self.repetition = repetition
    self.is_warmup = is_warmup
    self.temperature = temperature
    self.name = name
    self.probes = []
    self.timing = Timing()
    self.is_success = True
    self.index = index
    self.story = story
    self.out_dir = (
        browser_session.root_dir / safe_filename(self.browser.unique_name) /
        "stories" / name / f"repetition={self.repetition}" / self.temperature)
    self.group_dir = self.out_dir.parent
    self.did_setup = False
    self.did_run = False
    self.did_teardown = False
    self.did_teardown_browser = False
    self.is_dry_run: Optional[bool] = None

  def validate_env(self, env: HostEnvironment):
    pass

  def setup(self, is_dry_run: bool) -> None:
    assert self.is_dry_run is None
    self.is_dry_run = is_dry_run
    assert not self.did_setup
    self.did_setup = True

  def actions(self,
              name: str,
              verbose: bool = False,
              measure: bool = True) -> Actions:
    return Actions(name, self, verbose=verbose, measure=measure)

  @property
  def exceptions(self) -> Annotator:
    return self._exceptions

  def max_end_datetime(self) -> dt.datetime:
    return dt.datetime.max

  def run(self, is_dry_run: bool) -> None:
    assert self.is_dry_run is is_dry_run
    assert not self.did_run
    self.did_run = True

  def teardown(self, is_dry_run: bool) -> None:
    assert self.is_dry_run is is_dry_run
    assert not self.did_teardown
    self.did_teardown = True

  def _teardown_browser(self, is_dry_run: bool) -> None:
    assert self.is_dry_run is is_dry_run
    assert not self.did_teardown_browser
    self.did_teardown_browser = True
    self.browser.quit()

  def __repr__(self):
    return f"MockRun({self.name}, id={hex(id(self))})"

  def __str__(self):
    return self.name


class MockPlatform:

  def __init__(self, name) -> None:
    self.name = name

  def __str__(self):
    return self.name


class MockRunner:

  def __init__(self) -> None:
    self.benchmark = MockBenchmark(stories=[MockStory("mock_story")])
    self.runs = tuple()
    self.platform = MockPlatform("test-platform")
    self.repetitions = 1
    self.create_symlinks = True
    self.probes = []
    self.browsers = []
    self.out_dir = pathlib.Path("results/out")
    self.timing = Timing()
    self.env = HostEnvironment(self.platform, self.out_dir, self.browsers,
                               self.probes, self.repetitions)


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
        MockChromeDev("chrome-dev", settings=Settings(platform=self.platform)),
        MockFirefox(
            "firefox-stable", settings=Settings(platform=self.platform))
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
