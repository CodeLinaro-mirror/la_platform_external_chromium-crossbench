# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime as dt
import logging
import re
from typing import TYPE_CHECKING, override

from crossbench.benchmarks.loading.config.login.base import PresetLoginBlock
from crossbench.cli.config.secrets import GoogleUsernamePassword
from crossbench.plt.android_adb import AndroidAdbPlatform

if TYPE_CHECKING:
  from mobly.controllers import android_device

  from crossbench.action_runner.action_runner import ActionRunner
  from crossbench.cli.config.secrets import UsernamePassword
  from crossbench.env.runner_env import RunnerEnv
  from crossbench.runner.run import Run


class GoogleOsLogin(PresetLoginBlock):
  """Provisions an OS-level Google account and links the Chrome profile."""

  def _validate_and_get_secret(self, run: Run) -> UsernamePassword:
    self.validate_run(run)
    if not (secret := run.secrets.google):
      raise RuntimeError("No google login provided")
    if run.browser_platform.is_chromeos:
      return secret
    if (
      not isinstance(secret, GoogleUsernamePassword)
      or not secret.account_util_apk
    ):
      raise ValueError(
        "login: 'google-os' requires secrets.google.account_util_apk"
      )
    return secret

  @override
  def validate_env(self, env: RunnerEnv, run: Run) -> None:
    del env
    self._validate_and_get_secret(run)

  @override
  def validate_run(self, run: Run) -> None:
    super().validate_run(run)
    platform = run.browser_platform
    if platform.is_chromeos:
      return
    if not isinstance(platform, AndroidAdbPlatform):
      raise NotImplementedError(
        f"login: 'google-os' is only supported on Android ADB, got {platform}"
      )
    _ = run.browser.android_package

  @override
  def run_os_login(self, runner: ActionRunner) -> None:
    run = runner.run
    secret = self._validate_and_get_secret(run)
    if self.is_logged_in(run, secret, strict=True):
      return
    platform = run.browser_platform
    if platform.is_chromeos:
      raise RuntimeError(
        f"ChromeOS OS account is not logged into {secret.username!r}"
      )
    assert isinstance(secret, GoogleUsernamePassword)
    assert isinstance(platform, AndroidAdbPlatform)
    with run.actions("OS Login", measure=False):
      platform.provision_google_account(secret)

  @override
  def run_browser_login(self, runner: ActionRunner) -> None:
    run = runner.run
    secret = self._validate_and_get_secret(run)
    if self.is_logged_in(run, secret, strict=True):
      return
    platform = run.browser_platform
    if platform.is_chromeos:
      raise RuntimeError(
        f"ChromeOS OS account is not logged into {secret.username!r}"
      )
    assert isinstance(secret, GoogleUsernamePassword)
    assert isinstance(platform, AndroidAdbPlatform)
    package = run.browser.android_package

    with run.actions("Login", measure=False) as action:
      action.show_url("chrome://newtab/")
      with platform.uiautomator_device(root_device=False) as device:
        self._click_chrome_signin_flow(
          device, platform, package, secret.username
        )
        if self._has_chrome_identity_error(device, package):
          logging.info(
            "OS Google account %s has an expired token; re-provisioning.",
            secret.username,
          )
          platform.provision_google_account(secret, force=True)
          action.show_url("chrome://newtab/")
          self._click_chrome_signin_flow(
            device, platform, package, secret.username
          )
          if self._has_chrome_identity_error(device, package):
            raise RuntimeError(
              f"Chrome identity error persisted for {secret.username!r} "
              "after re-provisioning OS Google account"
            )

  def _has_chrome_identity_error(
    self, device: android_device.AndroidDevice, package: str
  ) -> bool:
    pkg = re.escape(package)
    return any(
      "verify" in str(banner.get("text", "")).lower()
      for banner in device.ui.find(resourceIdMatches=rf"{pkg}:id/message_title")
    )

  def _click_chrome_signin_flow(
    self,
    device: android_device.AndroidDevice,
    platform: AndroidAdbPlatform,
    package: str,
    username: str,
  ) -> None:
    pkg = re.escape(package)
    avatar = device.ui(
      resourceIdMatches=rf"{pkg}:id/(optional_toolbar_button|avatar_button)"
    )
    avatar.wait.exists(timeout=dt.timedelta(seconds=10), raise_error=True)
    if username.lower() in (avatar.description or "").lower():
      logging.info("Chrome already signed into %s", username)
      return
    if not avatar.click():
      raise RuntimeError(f"Failed to click Chrome identity disc on {package}")
    continue_btn = device.ui(
      resourceIdMatches=rf"{pkg}:id/account_picker_continue_as_button"
    )
    if not continue_btn.wait.click(timeout=dt.timedelta(seconds=10)):
      raise RuntimeError(
        f"Failed to click Chrome account picker button for {username}"
      )
    history_sync = device.ui(resourceIdMatches=rf"{pkg}:id/history_sync.*")
    if history_sync.wait.exists(timeout=dt.timedelta(seconds=5)):
      logging.info("Dismissing Chrome history sync prompt.")
      decline_btn = device.ui(resourceIdMatches=rf"{pkg}:id/button_secondary")
      if not decline_btn.wait.click(timeout=dt.timedelta(seconds=5)):
        raise RuntimeError("Failed to dismiss Chrome history sync prompt")
    platform.sleep(1.5)
