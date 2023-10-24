# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import shlex
from typing import TYPE_CHECKING, Dict, Iterable
from crossbench import cli_helper, plt
from crossbench.browsers.browser import Browser
from crossbench.browsers.chromium import chromium

from crossbench.probes.probe import (Probe, ProbeConfigParser, ProbeContext,
                                     ProbeValidationError, ResultLocation)
from crossbench.probes.results import EmptyProbeResult, ProbeResult

if TYPE_CHECKING:
  from crossbench.browsers.browser import Browser
  from crossbench.runner.run import Run
  from crossbench.env import HostEnvironment

_DEBUGGER_LOOKUP: Dict[str, str] = {
    "macos": "lldb",
    "linux": "gdb",
}

DEFAULT_GEOMETRY = "80x70"


class DebuggerProbe(Probe):
  """
  Probe debugging chrome's renderer process.
  """
  NAME = "debugger"
  RESULT_LOCATION = ResultLocation.BROWSER
  IS_GENERAL_PURPOSE = True

  @classmethod
  def config_parser(cls) -> ProbeConfigParser:
    parser = super().config_parser()
    parser.add_argument(
        "debugger",
        type=cli_helper.parse_binary_path,
        default=_DEBUGGER_LOOKUP.get(plt.PLATFORM.name,
                                     "debugger probe not supported"),
        help="Set a custom debugger binary. "
        "Currently only gdb and lldb are supported.")
    parser.add_argument(
        "auto_run",
        type=bool,
        default=True,
        help="Automatically start the renderer process in the debugger.")
    parser.add_argument(
        "geometry",
        type=str,
        default=DEFAULT_GEOMETRY,
        help="Geometry of the terminal (xterm) used to display the debugger.")
    parser.add_argument(
        "args",
        type=str,
        default=None,
        is_list=True,
        help="Additional args that are passed to the debugger.")
    return parser

  def __init__(
      self,
      debugger: pathlib.Path,
      auto_run: bool = True,
      geometry: str = DEFAULT_GEOMETRY,
      args: Iterable[str] = ()) -> None:
    super().__init__()
    self._debugger_bin = debugger
    self._debugger_args = args
    self._auto_run = auto_run
    self._geometry = geometry

  def validate_browser(self, env: HostEnvironment, browser: Browser) -> None:
    super().validate_browser(env, browser)
    self.expect_browser(browser, chromium.Chromium)
    # TODO: support more platforms
    if not (browser.platform.is_macos or browser.platform.is_linux):
      raise ValueError(f"Only supported on linux and macOS, but got {browser}")
    if browser.platform.is_remote:
      raise ProbeValidationError(self, "Does not run on remote platforms.")
    # TODO: support more terminals.
    if not browser.platform.which("xterm"):
      raise ProbeValidationError(self, "Please install xterm on your system.")

  def attach(self, browser: Browser) -> None:
    super().attach(browser)
    assert isinstance(browser, chromium.Chromium)
    flags = browser.flags
    flags.set("--no-sandbox")
    flags.set("--disable-hang-monitor")
    flags["--renderer-cmd-prefix"] = self.renderer_cmd_prefix()

  def renderer_cmd_prefix(self) -> str:
    # TODO: support more terminals.
    debugger_cmd = [
        "xterm",
        "-title",
        "renderer",
        "-geometry",
        self._geometry,
        "-e",
        str(self._debugger_bin),
    ]
    if self._debugger_bin.name == "lldb":
      if self._auto_run:
        debugger_cmd += ["-o", "run"]
      debugger_cmd += ["--"]
    else:
      assert self._debugger_bin.name == "gdb", (
          f"Unsupported debugger: {self._debugger_bin}")
      if self._auto_run:
        debugger_cmd += ["-ex", "run"]
      debugger_cmd += ["--args"]
    if self._debugger_args is not None:
      debugger_cmd.extend(self._debugger_args)
    return shlex.join(debugger_cmd)

  def get_context(self, run: Run) -> DebuggerContext:
    return DebuggerContext(self, run)


class DebuggerContext(ProbeContext[DebuggerProbe]):

  def start(self) -> None:
    pass

  def stop(self) -> None:
    pass

  def tear_down(self) -> ProbeResult:
    return EmptyProbeResult()
