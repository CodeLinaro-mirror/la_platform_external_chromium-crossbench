# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from typing import TYPE_CHECKING, Final, override

from crossbench.action_runner.action.action_type import ActionType
from crossbench.benchmarks.loading.config.blocks import ActionBlock
from crossbench.plt.android_adb import AndroidAdbPlatform

if TYPE_CHECKING:
  from crossbench.action_runner.action_runner import ActionRunner
  from crossbench.cli.config.secrets import UsernamePassword
  from crossbench.env.runner_env import RunnerEnv
  from crossbench.runner.run import Run


class BaseLoginBlock(ActionBlock):
  LABEL: Final[str] = "login"

  @override
  def validate(self) -> None:
    super().validate()
    assert self.index == 0, (
      f"Login block has to be the first, but got {self.index}"
    )

  @property
  def has_start_browser_action(self) -> bool:
    return any(action.TYPE is ActionType.START_BROWSER for action in self)

  def validate_env(self, env: RunnerEnv, run: Run) -> None:
    del env
    self.validate_run(run)

  def validate_run(self, run: Run) -> None:
    platform = run.browser_platform
    if isinstance(platform, AndroidAdbPlatform) and not platform.bypass_oobe:
      raise ValueError(
        f"Cannot run {type(self).__name__} on Android when bypass_oobe=False."
      )
    if platform.is_chromeos and not run.browser.settings.start_browser:
      raise NotImplementedError(
        f"Cannot run {type(self).__name__} on ChromeOS with --no-start-browser."
      )

  def run_os_login(self, runner: ActionRunner) -> None:
    self.validate_run(runner.run)

  def run_browser_login(self, runner: ActionRunner) -> None:
    super().run_with(runner)

  @override
  def run_with(self, runner: ActionRunner) -> None:
    self.run_os_login(runner)
    self.run_browser_login(runner)

  @property
  @override
  def is_login(self) -> bool:
    return True

  def is_logged_in(
    self, run: Run, secret: UsernamePassword, strict: bool = False
  ) -> bool:
    return run.browser.is_logged_in(secret, strict)


class PresetLoginBlock(BaseLoginBlock):
  @override
  def validate_actions(self) -> None:
    """Skip validation, since PresetLoginBlocks have an unknown number
    of actions."""

  def __len__(self) -> int:
    """LoginBlocks will have at least one action. Given they're not known
    upfront we set this to 1. This also ensures that bool(login_block) is
    True."""
    return 1
