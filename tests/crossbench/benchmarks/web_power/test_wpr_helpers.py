# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
import unittest

from crossbench.benchmarks.web_power.wpr_helpers import WprBannerDismisser
from tests import test_helper


class WprBannerDismisserTestCase(unittest.TestCase):

  def test_create_rules_with_role(self) -> None:
    metadata = 'Dismisser target: a,button,"Agree",https://www.cnn.com/'
    res = WprBannerDismisser.create_rules(metadata)
    self.assertIsNotNone(res)
    assert res is not None
    js_payload, target_url = res
    self.assertEqual(target_url, "https://www.cnn.com/")
    self.assertIn('const ELEMENT_TYPE = "a";', js_payload)
    self.assertIn('const ELEMENT_ROLE = "button";', js_payload)
    self.assertIn('const ELEMENT_TEXT = "Agree";', js_payload)

  def test_create_rules_without_role(self) -> None:
    metadata = (
        "Main URL: https://www.allrecipes.com\n"
        "Recording date: 2026-08-20\n"
        'Dismisser target: button,,"Accept All",https://www.allrecipes.com/\n'
    )
    res = WprBannerDismisser.create_rules(metadata)
    self.assertIsNotNone(res)
    assert res is not None
    js_payload, target_url = res
    self.assertEqual(target_url, "https://www.allrecipes.com/")
    self.assertIn('const ELEMENT_TYPE = "button";', js_payload)
    self.assertIn('const ELEMENT_ROLE = "";', js_payload)
    self.assertIn('const ELEMENT_TEXT = "Accept All";', js_payload)

  def test_create_rules_none(self) -> None:
    metadata = "Main URL: https://www.allrecipes.com\nRecording date: 2026-08-20\n"
    self.assertIsNone(WprBannerDismisser.create_rules(metadata))
    self.assertIsNone(WprBannerDismisser.create_rules(""))

  def test_serialize_rules(self) -> None:
    js_payload = 'console.log("dismiss");'
    target_url = "https://www.allrecipes.com/"
    rules_file = WprBannerDismisser.serialize_rules(js_payload, target_url)
    self.assertTrue(rules_file.exists())
    with rules_file.open("r", encoding="utf-8") as f:
      (rule,) = json.load(f)
    self.assertEqual(rule["URLPattern"], target_url)
    injected_script = rules_file.parent / rule["InjectedScript"]
    self.assertTrue(injected_script.exists())
    self.assertEqual(injected_script.read_text(encoding="utf-8"), js_payload)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
