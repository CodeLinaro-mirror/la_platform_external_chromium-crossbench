# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt

import crossbench.path as pth
from crossbench.benchmarks.loading.action import (
    ACTION_TIMEOUT, ActionType, ClickAction, GetAction,
    InjectNewDocumentScriptAction, ReadyState, ScrollAction, SwipeAction,
    TapAction, WaitAction, WaitForElementAction, WindowTarget)
from tests import test_helper
from tests.crossbench.mock_helper import CrossbenchFakeFsTestCase


class ActionTestCase(CrossbenchFakeFsTestCase):

  def test_parse_get_default(self):
    config_dict = {"action": "get", "url": "http://crossben.ch"}
    action = GetAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.GET)
    self.assertEqual(action.url, "http://crossben.ch")
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.duration, dt.timedelta())
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = GetAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_get_all(self):
    config_dict = {
        "action": "get",
        "url": "http://crossben.ch",
        "duration": "12s",
        "timeout": "34s",
        "ready_state": "any",
        "target": "_top"
    }
    action = GetAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.GET)
    self.assertEqual(action.url, "http://crossben.ch")
    self.assertEqual(action.timeout, dt.timedelta(seconds=34))
    self.assertEqual(action.duration, dt.timedelta(seconds=12))
    self.assertEqual(action.ready_state, ReadyState.ANY)
    self.assertEqual(action.target, WindowTarget.TOP)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = GetAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_get_invalid_url(self):
    with self.assertRaises(ValueError) as cm:
      GetAction.load_dict({
          "action": "get",
          "url": "",
      })
    self.assertIn("url", str(cm.exception))

  def test_parse_get_invalid_duration(self):
    with self.assertRaises(ValueError) as cm:
      GetAction.load_dict({
          "action": "get",
          "url": "http://crossben.ch",
          "duration": "-12s"
      })
    self.assertIn("duration", str(cm.exception))

  def test_parse_get_invalid_duration_for_ready_state(self):
    with self.assertRaises(ValueError):
      GetAction.load_dict({
          "action": "get",
          "url": "http://crossben.ch",
          "ready_state": "interactive",
          "duration": "12s"
      })

  def test_parse_wait_default(self):
    config_dict = {"action": "wait", "duration": "12s"}
    action = WaitAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.WAIT)
    self.assertEqual(action.duration, dt.timedelta(seconds=12))
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = WaitAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_wait_missing_duration(self):
    with self.assertRaises(ValueError) as cm:
      WaitAction.load_dict({"action": "wait"})
    self.assertIn("duration", str(cm.exception))

  def test_parse_scroll_default(self):
    config_dict = {"action": "scroll"}
    action = ScrollAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.SCROLL)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.duration, dt.timedelta(seconds=1))
    self.assertEqual(action.distance, 500)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = ScrollAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_scroll_all(self):
    config_dict = {
        "action": "scroll",
        "distance": "123",
        "timeout": "12s",
        "duration": "34s"
    }
    action = ScrollAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.SCROLL)
    self.assertEqual(action.timeout, dt.timedelta(seconds=12))
    self.assertEqual(action.duration, dt.timedelta(seconds=34))
    self.assertEqual(action.distance, 123)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = ScrollAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_scroll_invalid_distance(self):
    with self.assertRaises(ValueError) as cm:
      ScrollAction.load_dict({"action": "scroll", "distance": ""})
    self.assertIn("distance", str(cm.exception))
    with self.assertRaises(ValueError) as cm:
      ScrollAction.load_dict({"action": "scroll", "distance": "0"})
    self.assertIn("distance", str(cm.exception))

  def test_parse_click_default(self):
    config_dict = {"action": "click", "selector": "#button"}
    action = ClickAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.CLICK)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.selector, "#button")
    self.assertFalse(action.required)
    self.assertFalse(action.scroll_into_view)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = ClickAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_click_all(self):
    config_dict = {
        "action": "click",
        "selector": "#button",
        "required": True,
        "scroll_into_view": True,
        "timeout": "12s"
    }
    action = ClickAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.CLICK)
    self.assertEqual(action.timeout, dt.timedelta(seconds=12))
    self.assertEqual(action.selector, "#button")
    self.assertTrue(action.required)
    self.assertTrue(action.scroll_into_view)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = ClickAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_click_invalid_selector(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.load_dict({"action": "click", "selector": ""})
    self.assertIn("selector", str(cm.exception))

  def test_pase_click_unused_duration(self):
    input_dict = {"action": "click", "selector": "#button", "duration": "12s"}
    ClickAction.load_dict(input_dict)
    self.assertDictEqual(input_dict, {"duration": "12s"})

  def test_parse_tap_default(self):
    config_dict = {"action": "tap", "selector": "#button"}
    action = TapAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.TAP)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.selector, "#button")
    self.assertIsNone(action.x)
    self.assertIsNone(action.y)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = TapAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_tap_position(self):
    config_dict = {"action": "tap", "x": 100, "y": 200, "timeout": "12s"}
    action = TapAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.TAP)
    self.assertEqual(action.timeout, dt.timedelta(seconds=12))
    self.assertIsNone(action.selector)
    self.assertEqual(action.x, 100)
    self.assertEqual(action.y, 200)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = TapAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_tap_invalid(self):
    with self.assertRaises(ValueError) as cm:
      TapAction.load_dict({
          "action": "tap",
          "selector": "#button",
          "x": 100,
          "y": 200,
      })
    self.assertIn("selector", str(cm.exception))

  def test_parse_swipe(self):
    config_dict = {
        "action": "swipe",
        "startx": 100,
        "starty": 200,
        "endx": 110,
        "endy": 220,
        "duration": "12s"
    }
    action = SwipeAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.SWIPE)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.duration, dt.timedelta(seconds=12))
    self.assertEqual(action.startx, 100)
    self.assertEqual(action.starty, 200)
    self.assertEqual(action.endx, 110)
    self.assertEqual(action.endy, 220)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = SwipeAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_wait_for_element(self):
    config_dict = {
        "action": "wait_for_element",
        "selector": "#button",
    }
    action = WaitForElementAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.WAIT_FOR_ELEMENT)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.selector, "#button")
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = WaitForElementAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_wait_for_element_timeout(self):
    config_dict = {
        "action": "wait_for_element",
        "selector": "#button",
        "timeout": "12s"
    }
    action = WaitForElementAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.WAIT_FOR_ELEMENT)
    self.assertEqual(action.timeout, dt.timedelta(seconds=12))
    self.assertEqual(action.selector, "#button")
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = WaitForElementAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_inject_new_document_script(self):
    config_dict = {
        "action": "inject_new_document_script",
        "script": "alert(1)",
    }
    action = InjectNewDocumentScriptAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.INJECT_NEW_DOCUMENT_SCRIPT)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.script, "alert(1)")
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = InjectNewDocumentScriptAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_inject_new_document_script_path(self):
    path = self.create_file("/foo/bar.js", contents="alert(2)")
    config_dict = {
        "action": "inject_new_document_script",
        "script_path": str(path),
    }
    action = InjectNewDocumentScriptAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.INJECT_NEW_DOCUMENT_SCRIPT)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.script, "alert(2)")
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = InjectNewDocumentScriptAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_inject_new_document_script_path_with_replacements(self):
    path = self.create_file("/foo/bar.js", contents="alert($ALERT$)")
    config_dict = {
        "action": "inject_new_document_script",
        "script_path": str(path),
        "replace": {
            "$ALERT$": "'something'"
        }
    }
    action = InjectNewDocumentScriptAction.load_dict(config_dict)
    self.assertFalse(config_dict)
    self.assertEqual(action.TYPE, ActionType.INJECT_NEW_DOCUMENT_SCRIPT)
    self.assertEqual(action.script, "alert('something')")
    action.validate()

    action_2 = InjectNewDocumentScriptAction.load_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_inject_new_document_script_invalid(self):
    config_dict = {
        "action": "inject_new_document_script",
        "script": "",
    }
    with self.assertRaises(ValueError) as cm:
      InjectNewDocumentScriptAction.load_dict(config_dict)
    self.assertIn("script", str(cm.exception))
    self.assertFalse(config_dict)

  def test_inject_new_document_script_invalid_path(self):
    config_dict = {
        "action": "inject_new_document_script",
        "script_path": "",
    }
    with self.assertRaises(ValueError) as cm:
      InjectNewDocumentScriptAction.load_dict(config_dict)
    self.assertIn("script_path", str(cm.exception))
    self.assertFalse(config_dict)
    config_dict = {
        "action": "inject_new_document_script",
        "script_path": "/does/not/exist.js",
    }
    with self.assertRaises(ValueError) as cm:
      InjectNewDocumentScriptAction.load_dict(config_dict)
    self.assertIn("script_path", str(cm.exception))
    self.assertFalse(config_dict)

  def test_inject_new_document_script_invalid_script_xor_path(self):
    path = self.create_file("/foo/bar.js", contents="alert(2)")
    config_dict = {
        "action": "inject_new_document_script",
        "script": "alert(1)",
        "script_path": str(path),
    }
    with self.assertRaises(ValueError) as cm:
      InjectNewDocumentScriptAction.load_dict(config_dict)
    self.assertIn("script_path", str(cm.exception))
    self.assertFalse(config_dict)

  def test_inject_new_document_script_invalid_replacements(self):
    path = self.create_file("/foo/bar.js", contents="alert(2)")
    config_dict = {
        "action": "inject_new_document_script",
        "script_path": str(path),
        "replacements": {
            1: 1,
            "one": 1,
        }
    }
    with self.assertRaises(ValueError) as cm:
      InjectNewDocumentScriptAction.load_dict(config_dict)
    self.assertIn("replacements", str(cm.exception))
    self.assertFalse(config_dict)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
