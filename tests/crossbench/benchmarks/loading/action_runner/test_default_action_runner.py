# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import pathlib

from crossbench.action_runner.action.probe import ProbeAction
from crossbench.action_runner.default_action_runner import DefaultActionRunner
from crossbench.benchmarks.loading.config.blocks import ActionBlock
from crossbench.browsers.settings import Settings
from crossbench.exception import MultiException
from crossbench.flags.base import Flags
from crossbench.probes.js import JSProbe
from crossbench.probes.probe import Probe
from crossbench.probes.screenshot import ScreenshotProbe
from crossbench.runner.groups.session import BrowserSessionRunGroup
from tests import test_helper
from tests.crossbench.action_runner.action_runner_test_case import \
    ActionRunnerTestCase
from tests.crossbench.mock_browser import MockChromeStable
from tests.crossbench.mock_helper import LinuxMockPlatform
from tests.crossbench.runner.helper import MockRun, MockRunner


class DefaultActionRunnerTestCase(ActionRunnerTestCase):

  def set_up_with_probe(self, probe: Probe) -> None:
    pathlib.Path("/usr/bin").mkdir(parents=True, exist_ok=True)
    pathlib.Path("/usr/bin/google-chrome").write_text("definitely a browser")

    self.root_dir = pathlib.Path()
    self.platform = LinuxMockPlatform()
    self.browser = MockChromeStable(
        "mock browser", settings=Settings(platform=self.platform))
    self.probe = probe
    self.runner = MockRunner(probes=[self.probe])
    self.root_dir = pathlib.Path()
    self.session = BrowserSessionRunGroup(self.runner.env,
                                          self.runner.probes, self.browser,
                                          Flags(), 1, self.root_dir, True, True)
    self.action_runner = DefaultActionRunner()
    self.run = MockRun(
        self.runner,
        self.session,
        "run 1",
        self.action_runner,
        probe=self.probe)
    self.probe_context = self.probe.get_context_cls()(self.probe, self.run)
    self.run.set_probe_context(self.probe_context)

  def test_probe_action_unsupported_probe(self):
    self.set_up_with_probe(JSProbe(""))
    action_block = ActionBlock(actions=[ProbeAction(probe="js", kwargs={})])

    with self.assertRaisesRegex(MultiException,
                                "Invoke not implemented for probe"):
      self.action_runner.run_block(self.run, action_block)

  def test_probe_action_screenshot(self):
    self.set_up_with_probe(ScreenshotProbe())
    action_block = ActionBlock(
        actions=[ProbeAction(probe="screenshot", kwargs={})])
    self.action_runner.run_block(self.run, action_block)
    self.assertEqual(len(self.platform.screenshots), 1)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
