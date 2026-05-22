# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import atexit
import json
import re
import tempfile

from crossbench import path as pth

_ENCODING = "utf-8"


class WprBannerDismisser:
  """Configures WebPageReplay to automatically inject cookie banner dismissers.

  Reads embedded metadata from the WPR archive files to discover target banner
  strings, instantiates client-side dismissal scripts, and generates the proxy
  network transformation rules required to inject them.

  It is assumed that the format used is as follows:
   - Any line that does not start with "Dismisser target:" may be ignored.
   - There is at most a single such line.
   - The line, if it exists, is formatted as follows:
        Dismisser target: <type>,<role>,"<text>",<target_url>
     For example:
        Dismisser target: a,button,"Agree",https://www.cnn.com/
   - In the above line, the elements are:
      1. The element type (e.g. "button", "a", "input") is the tag name of the
         element to dismiss.
      2. The element role (e.g. "button", "link", "input") is the ARIA role of
         the element to dismiss.
      3. The element text (e.g. "Accept all cookies", "Decline all cookies") is
         the text content of the element to dismiss.
      4. The target URL (e.g. "https://www.cnn.com") is the URL of the page to
         dismiss the banner on.

    The banner dismisser uses a MutationObserver to wait for the element
    to appear on the page and click it.
  """

  @classmethod
  def create_rules(cls, metadata: str) -> tuple[str, str] | None:
    match = re.search(
        r"^Dismisser target:\s*([^,]+),([^,]+),\"([^\"]*)\",([^\n]+)",
        metadata, re.MULTILINE)
    if not match:
      return None

    elem_type = match.group(1)
    elem_role = match.group(2)
    elem_text = match.group(3)
    target_url = match.group(4)

    js_payload = cls._build_dismisser_script(elem_type, elem_role, elem_text)
    return (js_payload, target_url)

  @classmethod
  def serialize_rules(cls, js_payload: str, target_url: str) -> pth.LocalPath:
    script_path: str = ""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding=_ENCODING, delete=False) as sf:
      sf.write(js_payload)
      script_path = sf.name
      atexit.register(pth.LocalPath(script_path).unlink, missing_ok=True)
    rules = [{"URLPattern": target_url, "InjectedScript": script_path}]
    with tempfile.NamedTemporaryFile(
        mode="w", encoding=_ENCODING, suffix=".json", delete=False) as rf:
      rf.write(json.dumps(rules, indent=2))
      atexit.register(pth.LocalPath(rf.name).unlink, missing_ok=True)
      return pth.LocalPath(rf.name)

  @classmethod
  def _build_dismisser_script(
      cls, elem_type: str, elem_role: str, elem_text: str) -> str:
    template_file = pth.LocalPath(__file__).parent / "dismisser.js"
    mapping = {
        "INJECTED_TYPE": f'"{elem_type}"',
        "INJECTED_ROLE": f'"{elem_role}"',
        "INJECTED_TEXT": f'"{elem_text}"',
    }
    return re.sub(
        r"INJECTED_(TYPE|ROLE|TEXT)",
        lambda m: mapping[m.group(0)],
        template_file.read_text(encoding=_ENCODING))
