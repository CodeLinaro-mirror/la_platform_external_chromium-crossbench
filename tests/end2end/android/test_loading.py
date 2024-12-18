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

def _run_loading_test(browser_config, page_config) -> None:
  with tempfile.NamedTemporaryFile() as page_config_file:
    with open(page_config_file.name, mode="w", encoding="utf-8") as f:
      json.dump(page_config, f)

    cli = CrossBenchCLI()

    cli.run([
        "loading", f"--browser={browser_config}",
        f"--page-config={page_config_file.name}", "--action-runner=android"
    ])


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
                      "position": {
                          "selector": "button[id='button']",
                          "required": True,
                          "scroll_into_view": True
                      },
                      "source": str(input_source),
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

  _run_loading_test(browser_config, page_config)


def test_scroll(browser_config) -> None:

  test_page = urllib.parse.quote("""
<!DOCTYPE html>
<html>
<head>
  <title>Scroll Test</title>
  <style>
    #scrollable-area {
      height: 200px;
      overflow-y: auto;
    }
    #content {
      height: 500px;
    }
  </style>
</head>
<body>
  <div id="no-scroll"></div>
  <div id="scrollable-area">
    <div id="content">
    </div>
  </div>
  <script>
    const scrollableArea = document.getElementById('scrollable-area');
    scrollableArea.addEventListener('scroll', function() {
      document.getElementById('no-scroll').id = 'yes-scroll';
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
                      "selector": "div[id='scrollable-area']",
                      "timeout": "10s"
                  },
                  {
                      "action": "scroll",
                      "selector": "div[id='scrollable-area']",
                      "required": True,
                      "source": "touch",
                      "distance": 50,
                  },
                  {
                      "action": "wait_for_element",
                      "selector": "div[id='yes-scroll']",
                      "timeout": "1s"
                  },
              ]
          }
      }
  }

  _run_loading_test(browser_config, page_config)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
