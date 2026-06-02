# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import pathlib
import unittest
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, call

from crossbench.action_runner.action.click import ClickAction
from crossbench.action_runner.action.probe import ProbeAction
from crossbench.action_runner.base import ActionRunner
from crossbench.benchmarks.loading.config.blocks import ActionBlock
from crossbench.browsers.settings import Settings
from crossbench.exception import MultiException
from crossbench.flags.base import Flags
from crossbench.probes.downloads import DownloadsProbe, \
    FileWatchDownloadsProbeContext
from crossbench.probes.dump_html import DumpHtmlProbe
from crossbench.probes.meminfo import MeminfoProbe
from crossbench.probes.screenshot import ScreenshotProbe
from crossbench.probes.shell import ShellProbe
from crossbench.runner.groups.session import BrowserSessionRunGroup
from crossbench.runner.run import Run
from tests import test_helper
from tests.crossbench.action_runner.action_runner_test_case import \
    ActionRunnerTestCase
from tests.crossbench.mock_browser import MockChromeStable
from tests.crossbench.mock_helper import LinuxMockPlatform
from tests.crossbench.runner.helper import MockRun, MockRunner

if TYPE_CHECKING:
  from crossbench.probes.probe import Probe, ProbeContext


class MockActionRunner(ActionRunner):

  def __init__(self, run: Run) -> None:
    super().__init__(run)
    self.click_js = MagicMock(name="Mock click_js")


class BaseActionRunnerTestCase(unittest.TestCase):

  def test_click_attempts_first_success(self):
    mock_run = MagicMock(name="Mock Run")
    mock_action_runner = MockActionRunner(mock_run)

    config_dict = {"action": "click", "selector": "#button", "attempts": 3}
    action = ClickAction.config_parser().parse(config_dict)

    mock_action_runner.click_js.side_effect = [None]

    mock_action_runner.click(action)

    mock_action_runner.click_js.assert_called_once_with(action)

  def test_click_attempts_last_success(self):
    mock_run = MagicMock(name="Mock Run")
    mock_action_runner = MockActionRunner(mock_run)

    config_dict = {"action": "click", "selector": "#button", "attempts": 3}
    action = ClickAction.config_parser().parse(config_dict)

    mock_action_runner.click_js.side_effect = [
        Exception("fail first"),
        Exception("and second"),
        None,
    ]

    mock_action_runner.click(action)

    mock_action_runner.click_js.assert_has_calls([
        call(action),
        call(action),
        call(action),
    ])

  def test_click_attempts_fail(self):
    mock_run = MagicMock(name="Mock Run")
    mock_action_runner = MockActionRunner(mock_run)

    config_dict = {"action": "click", "selector": "#button", "attempts": 3}
    action = ClickAction.config_parser().parse(config_dict)

    class TestException(Exception):
      pass

    mock_action_runner.click_js.side_effect = [
        TestException("fail first"),
        TestException("and second"),
        TestException("and third"),
    ]

    with self.assertRaises(TestException):
      mock_action_runner.click(action)

    mock_action_runner.click_js.assert_has_calls([
        call(action),
        call(action),
        call(action),
    ])


class DefaultActionRunnerTestCase(ActionRunnerTestCase):

  def set_up_with_probe(
      self,
      probe: Probe,
      probe_context_cls: type[ProbeContext] | None = None,
      probe_context_args: dict[str, Any] | None = None,
  ) -> None:
    self.fs.create_file(
        "/usr/bin/google-chrome", contents="definitely a browser")

    self.root_dir = pathlib.Path()
    self.platform = LinuxMockPlatform()
    self.browser = MockChromeStable(
        "mock browser", settings=Settings(platform=self.platform))
    self.probe = probe
    self.runner = MockRunner(probes=[self.probe])
    self.root_dir = pathlib.Path()
    self.session = BrowserSessionRunGroup(
        self.runner.env,
        self.runner.probes,
        self.browser,
        Flags(),
        1,
        self.root_dir,
        True,
        True,
    )
    self.mock_run: Any = MockRun(
        self.runner,
        self.session,
        "run 1",
        probe=self.probe,
    )
    self.action_runner = ActionRunner(self.mock_run)
    self.mock_run.action_runner = self.action_runner


    if not probe_context_cls:
      self.probe_context = self.probe.create_context(cast(Run, self.mock_run))
    else:
      self.probe_context = probe_context_cls(
          self.probe,
          cast(Run, self.mock_run),
          **(probe_context_args if probe_context_args else {}),
      )

    self.mock_run.set_probe_context(self.probe_context)

  def test_probe_action_unsupported_probe(self):
    self.set_up_with_probe(ShellProbe(""))
    action_block = ActionBlock(actions=(ProbeAction(probe="shell", kwargs={}),))

    with self.assertRaisesRegex(MultiException,
                                "Invoke not implemented for probe"):
      self.action_runner.run_block(self.mock_run, action_block)

  def test_probe_action_screenshot(self):
    self.set_up_with_probe(ScreenshotProbe())
    action_block = ActionBlock(
        actions=(ProbeAction(probe="screenshot", kwargs={}),))
    self.action_runner.run_block(self.mock_run, action_block)
    self.assertEqual(len(self.platform.screenshots), 1)

  def test_probe_action_wait_for_download_missing_pattern(self):
    self.set_up_with_probe(
        DownloadsProbe(),
        FileWatchDownloadsProbeContext,
        {"downloads_dir": "/Downloads"},
    )
    action_block = ActionBlock(
        actions=(ProbeAction(probe="downloads", kwargs={}),))

    with self.assertRaisesRegex(MultiException, "pattern"):
      self.action_runner.run_block(self.mock_run, action_block)

  def test_probe_action_wait_for_download(self):
    downloads_dir = pathlib.Path("/Downloads")
    downloads_dir.mkdir()
    self.set_up_with_probe(
        DownloadsProbe(),
        FileWatchDownloadsProbeContext,
        {"downloads_dir": downloads_dir},
    )
    action_block = ActionBlock(
        actions=(
            ProbeAction(probe="downloads", kwargs={"pattern": "a_download"}),))

    with self.assertRaisesRegex(MultiException, "Waited for"):
      self.action_runner.run_block(self.mock_run, action_block)

  def test_probe_action_meminfo_no_kwargs(self):
    self.set_up_with_probe(MeminfoProbe())
    action_block = ActionBlock(
        actions=(ProbeAction(probe="meminfo", kwargs={}),))

    self.action_runner.run_block(self.mock_run, action_block)
    self.assertEqual(self.browser.performance_marks[-1], "crossbench-meminfo")

  def test_probe_action_meminfo_all_kwargs(self):
    self.set_up_with_probe(MeminfoProbe())
    action_block = ActionBlock(
        actions=(ProbeAction(
            probe="meminfo",
            kwargs={
                "browser": False,
                "system": False,
                "packages": [],
                "title": "",
            },
        ),))

    self.action_runner.run_block(self.mock_run, action_block)
    self.assertEqual(self.browser.performance_marks[-1], "crossbench-meminfo")

  def test_probe_action_dump_html(self):
    self.set_up_with_probe(DumpHtmlProbe())
    action_block = ActionBlock(
        actions=(ProbeAction(probe="dump_html", kwargs={}),))
    self.browser.set_default_js_return(True)
    self.action_runner.run_block(self.mock_run, action_block)
    self.assertEqual(
        self.browser.invoked_js[-1].script,
        "return document.children[0].outerHTML",
    )


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
