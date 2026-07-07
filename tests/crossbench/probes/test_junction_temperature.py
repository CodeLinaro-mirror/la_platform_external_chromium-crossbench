# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from unittest import mock

from typing_extensions import override

from crossbench.probes.junction_temperature import JunctionTemperatureMode
from crossbench.probes.junction_temperature import \
    JunctionTemperatureProbe as JtProbe
from crossbench.probes.junction_temperature import \
    JunctionTemperatureProbeContext
from crossbench.probes.probe import ProbeIncompatibleBrowser
from crossbench.probes.results import LocalProbeResult
from tests import test_helper
from tests.crossbench.probes.helper import BaseProbeTestCase


def _rooted_cmd(cmd: str) -> tuple[str, ...]:
  return ("su", "0", "sh", "-c", cmd)


def _stats_reset() -> tuple[str, ...]:
  return _rooted_cmd(f"echo 1 > {JtProbe.stats_reset_path()}")


def _stats_collect() -> tuple[str, ...]:
  return _rooted_cmd(f"cat {JtProbe.stats_path()}")


class JunctionTemperatureProbeTestCase(BaseProbeTestCase):

  @override
  def setUp(self) -> None:
    super().setUp()
    self.probe = JtProbe()
    self.browser = self.magic_mock_browser
    self.browser.platform.is_android = True
    self.env = mock.MagicMock()

  def test_validate_browser_incompatible(self):
    self.browser.platform.is_android = False
    with self.assertRaises(ProbeIncompatibleBrowser):
      self.probe.validate_browser(self.env, self.browser)

  def test_validate_browser_success(self):
    self.browser.platform.sh_stdout.return_value = "uid=0(root) gid=0(root)"
    self.probe.validate_browser(self.env, self.browser)

  def test_validate_browser_root_failure_non_root(self):
    self.browser.platform.sh_stdout.return_value = (
        "uid=2000(shell) gid=2000(shell)")
    with self.assertRaises(ProbeIncompatibleBrowser) as cm:
      self.probe.validate_browser(self.env, self.browser)
    self.assertIn("Can't use root on this device", str(cm.exception))

  def test_validate_browser_root_failure_su_error(self):
    self.browser.platform.sh_stdout.side_effect = RuntimeError("su failed")
    with self.assertRaises(ProbeIncompatibleBrowser) as cm:
      self.probe.validate_browser(self.env, self.browser)
    self.assertIn("Can't use root on this device", str(cm.exception))

  def test_validate_browser_tmu_path_missing(self):
    # Mock the `test -d` command failure to verify validation fails
    # when the TMU path is missing.
    def sh_stdout_mock(*args, **kwargs):
      if "test" in args:
        raise RuntimeError("test -d failed")
      return "uid=0(root) gid=0(root)"

    self.browser.platform.sh_stdout.side_effect = sh_stdout_mock
    with self.assertRaises(ProbeIncompatibleBrowser) as cm:
      self.probe.validate_browser(self.env, self.browser)
    self.assertIn("TMU path missing", str(cm.exception))

  def _check_probe_lifecycle(
      self,
      mode: JunctionTemperatureMode,
      tmu_stats_output: str,
      steps: list[tuple[str, tuple[str, ...] | None]],
  ) -> None:
    probe = JtProbe(mode=mode)
    run = self.mock_run(result_path="/results/junction_temperature.txt")
    platform = run.browser_session.browser.platform
    platform.is_android = True
    platform.sh_stdout.return_value = tmu_stats_output

    context = probe.create_context(run)
    self.assertIsInstance(context, JunctionTemperatureProbeContext)

    expected_count = 0
    result = None
    for hook_name, expected_cmd in steps:
      hook = getattr(context, hook_name)
      result = hook()
      if expected_cmd:
        expected_count += 1
        platform.sh_stdout.assert_called_with(*expected_cmd)
      self.assertEqual(len(platform.sh_stdout.call_args_list), expected_count)

    self.assertIsInstance(result, LocalProbeResult)
    self.assertFalse(result.is_empty)
    self.assertEqual(len(result.file_list), 1)
    self.assertTrue(result.file.exists())
    self.assertEqual(result.file.name, "junction_temperature.txt")
    self.assertEqual(result.file.read_text(), tmu_stats_output)

  def test_probe_lifecycle_and_teardown(self):
    self._check_probe_lifecycle(
        mode=JunctionTemperatureMode.RUN,
        tmu_stats_output="tmu_stats data 123",
        steps=[
            ("setup", _stats_reset()),
            ("start", None),
            ("start_story_run", None),
            ("stop_story_run", None),
            ("stop", None),
            ("teardown", _stats_collect()),
        ],
    )

  def test_probe_lifecycle_story_mode(self):
    self._check_probe_lifecycle(
        mode=JunctionTemperatureMode.STORY,
        tmu_stats_output="tmu_stats data 456",
        steps=[
            ("setup", None),
            ("start", None),
            ("start_story_run", _stats_reset()),
            ("stop_story_run", _stats_collect()),
            ("stop", None),
            ("teardown", None),
        ],
    )

  def test_probe_teardown_without_start(self):
    probe = JtProbe()
    run = self.mock_run(result_path="/results/junction_temperature.txt")
    platform = run.browser_session.browser.platform
    platform.is_android = True

    context = probe.create_context(run)
    result = context.teardown()
    platform.sh_stdout.assert_not_called()
    self.assertTrue(result.is_empty)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
