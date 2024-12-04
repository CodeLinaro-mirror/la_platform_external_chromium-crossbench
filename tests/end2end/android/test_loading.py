# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
import tempfile
import urllib.parse

import pytest

from crossbench.benchmarks.loading.input_source import InputSource
from crossbench.cli.cli import CrossBenchCLI
from tests import test_helper


@pytest.mark.parametrize("input_source", InputSource)
def test_click(browser_config, input_source) -> None:

  if input_source is InputSource.KEYBOARD:
    return

  test_page = urllib.parse.quote("""
<!DOCTYPE html>
<html>
<body>
  <button id="button">Click me</button>
  <script>
    const button = document.getElementById('button');

    button.addEventListener('click',
    function() {
      button.id = "clicked-button";
    });
  </script>
</body>
</html>
""")

  page_config = {
      "pages": {
          "ClickTest": {
              "actions": [
                  {
                      "action": "get",
                      "url": f"data:text/html;charset=utf-8,{test_page}",
                      "ready_state": "complete"
                  },
                  {
                      "action": "wait_for_element",
                      "selector": "button[id='button']",
                      "timeout": "10s"
                  },
                  {
                      "action": "click",
                      "selector": "button[id='button']",
                      "required": True,
                      "source": str(input_source),
                      "scroll_into_view": True
                  },
                  {
                      "action": "wait_for_element",
                      "selector": "button[id='clicked-button']",
                      "timeout": "1s"
                  },
              ]
          }
      }
  }

  with tempfile.NamedTemporaryFile() as page_config_file:
    with open(page_config_file.name, mode="w", encoding="utf-8") as f:
      json.dump(page_config, f)

    cli = CrossBenchCLI()

    cli.run([
        "loading", f"--browser={browser_config}",
        f"--page-config={page_config_file.name}", "--action-runner=android"
    ])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
