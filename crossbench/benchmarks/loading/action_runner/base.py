# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Iterable, Optional

from crossbench.benchmarks.loading.input_source import InputSource

from crossbench import exception

if TYPE_CHECKING:
  from crossbench.benchmarks.loading import action as i_action
  from crossbench.benchmarks.loading.page_config import ActionBlock
  from crossbench.path import LocalPath
  from crossbench.runner.run import Run
  from crossbench.benchmarks.loading.page import Page, CombinedPage, InteractivePage


class ActionNotImplementedError(NotImplementedError):

  def __init__(self,
               runner: ActionRunner,
               action: i_action.Action,
               msg_context: str = "") -> None:
    self.runner = runner
    self.action = action

    if msg_context:
      msg_context = ". Context: " + msg_context

    message = (f"{str(action.TYPE).capitalize()}-action "
               f"not implemented in {type(runner).__name__}{msg_context}")
    super().__init__(message)


class InputSourceNotImplementedError(ActionNotImplementedError):

  def __init__(self,
               runner: ActionRunner,
               action: i_action.Action,
               input_source: InputSource,
               msg_context: str = "") -> None:

    if msg_context:
      msg_context = ". Context: " + msg_context

    input_source_message = (f"Source: '{input_source}'"
                            f"not implemented{msg_context}")

    super().__init__(runner, action, input_source_message)


class ActionRunner(abc.ABC):
  _info_stack: Optional[exception.TInfoStack]

  # info_stack is a unqiue identifier for the currently running or most recently
  # run action.
  @property
  def info_stack(self) -> exception.TInfoStack:
    if not self._info_stack:
      raise Exception("info_stack can not be called before run_blocks")
    return self._info_stack

  def run_blocks(self, run: Run, action_blocks: Iterable[ActionBlock]):
    for block_index, block in enumerate(action_blocks, start=1):
      # TODO: Instead maybe just pass context down. Or pass unique path to every action __init__
      with exception.annotate(f"Running block {block_index}: {block.label}"):
        for action_index, action in enumerate(block.actions, start=1):
          self._info_stack = (f"block_{block_index}", f"action_{action_index}")
          action.run_with(run, self)

  def wait(self, run: Run, action: i_action.WaitAction) -> None:
    with run.actions("WaitAction", measure=False) as actions:
      actions.wait(action.duration)

  def js(self, run: Run, action: i_action.JsAction) -> None:
    with run.actions("JS", measure=False) as actions:
      actions.js(action.script, action.timeout)

  def click(self, run: Run, action: i_action.ClickAction) -> None:
    input_source = action.input_source
    if input_source is InputSource.JS:
      self.click_js(run, action)
    elif input_source is InputSource.TOUCH:
      self.click_touch(run, action)
    elif input_source is InputSource.MOUSE:
      self.click_mouse(run, action)
    else:
      raise RuntimeError(f"Unsupported input source: '{input_source}'")

  def scroll(self, run: Run, action: i_action.ScrollAction) -> None:
    input_source = action.input_source
    if input_source is InputSource.JS:
      self.scroll_js(run, action)
    elif input_source is InputSource.TOUCH:
      self.scroll_touch(run, action)
    elif input_source is InputSource.MOUSE:
      self.scroll_mouse(run, action)
    else:
      raise RuntimeError(f"Unsupported input source: '{input_source}'")

  def get(self, run: Run, action: i_action.GetAction) -> None:
    raise ActionNotImplementedError(self, action)

  def click_js(self, run: Run, action: i_action.ClickAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def click_touch(self, run: Run, action: i_action.ClickAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def click_mouse(self, run: Run, action: i_action.ClickAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def scroll_js(self, run: Run, action: i_action.ScrollAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def scroll_touch(self, run: Run, action: i_action.ScrollAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def scroll_mouse(self, run: Run, action: i_action.ScrollAction) -> None:
    raise InputSourceNotImplementedError(self, action, action.input_source)

  def swipe(self, run: Run, action: i_action.SwipeAction) -> None:
    raise ActionNotImplementedError(self, action)

  def wait_for_element(self, run: Run,
                       action: i_action.WaitForElementAction) -> None:
    raise ActionNotImplementedError(self, action)

  def inject_new_document_script(
      self, run: Run, action: i_action.InjectNewDocumentScriptAction) -> None:
    raise ActionNotImplementedError(self, action)

  # screenshot_path is a helper for screenshot that generates the full path of a
  # screenshot file based on info_stack. The screenshot dir is created if
  # necessary.
  # TODO: the folder management should be done in a probe.
  def screenshot_path(self, out_dir: LocalPath, suffix: str) -> LocalPath:
    screenshot_path = out_dir / "screenshot"
    screenshot_path.mkdir(exist_ok=True)
    filename = "_".join(self.info_stack) + f"_{suffix}.png"
    return screenshot_path / filename

  # TODO: Move this into a probe, which can have multiple implementations for
  # different platforms or fullscreen vs. window, etc.
  def screenshot_impl(self, run: Run, suffix: str) -> None:
    run.browser.screenshot(self.screenshot_path(run.out_dir, suffix))

  def screenshot(self, run: Run, _action: i_action.ScreenshotAction) -> None:
    self.screenshot_impl(run, "screenshot")

  def run_page(self, run: Run, page: Page):
    run.browser.show_url(run.runner, page.url)
    run.runner.wait(page.duration)
    page._maybe_navigate_to_about_blank(run)

  def run_interactive_page(self, run: Run, page: InteractivePage):
    try:
      page.action_runner.run_blocks(run, page.action_blocks)
    except Exception:
      page.failure_screenshot(run)
      raise

  def run_combined_page(self, run: Run, page: CombinedPage):
    for i, sub_page in enumerate(page.pages):
      # Create a new tab for the multiple_tab case.
      if i > 0 and page._tabs.multiple_tabs:
        browser = run.browser
        browser.switch_to_new_tab()
      sub_page.run_with(run, self)
