# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt

from crossbench.benchmarks.loading.action import (
    ACTION_TIMEOUT, ActionType, ClickAction, GetAction,
    InjectNewDocumentScriptAction, JsAction, ReadyState, ScrollAction,
    SwipeAction, SwitchTabAction, TextInputAction, WaitAction,
    WaitForElementAction, WaitForReadyStateAction, WindowTarget)
from crossbench.benchmarks.loading.input_source import InputSource
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


class ActionTestCase(CrossbenchFakeFsTestCase):

  def test_parse_get_default(self):
    config_dict = {"action": "get", "url": "http://crossben.ch"}
    action = GetAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.GET)
    self.assertEqual(action.url, "http://crossben.ch")
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.duration, dt.timedelta())
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = GetAction.parse_dict(action.to_json())
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
    action = GetAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.GET)
    self.assertEqual(action.url, "http://crossben.ch")
    self.assertEqual(action.timeout, dt.timedelta(seconds=34))
    self.assertEqual(action.duration, dt.timedelta(seconds=12))
    self.assertEqual(action.ready_state, ReadyState.ANY)
    self.assertEqual(action.target, WindowTarget.TOP)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = GetAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_get_new_tab(self):
    config_dict = {
        "action": "get",
        "url": "http://crossben.ch",
        "target": "_new_tab"
    }
    action = GetAction.parse_dict(config_dict)
    self.assertEqual(action.target, WindowTarget.NEW_TAB)
    action.validate()

    action_2 = GetAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_get_new_window(self):
    config_dict = {
        "action": "get",
        "url": "http://crossben.ch",
        "target": "_new_window"
    }
    action = GetAction.parse_dict(config_dict)
    self.assertEqual(action.target, WindowTarget.NEW_WINDOW)
    action.validate()

    action_2 = GetAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_get_invalid_url(self):
    with self.assertRaises(ValueError) as cm:
      GetAction.parse_dict({
          "action": "get",
          "url": "",
      })
    self.assertIn("url", str(cm.exception))

  def test_parse_get_invalid_duration(self):
    with self.assertRaises(ValueError) as cm:
      GetAction.parse_dict({
          "action": "get",
          "url": "http://crossben.ch",
          "duration": "-12s"
      })
    self.assertIn("duration", str(cm.exception))

  def test_parse_get_invalid_duration_for_ready_state(self):
    with self.assertRaises(ValueError):
      GetAction.parse_dict({
          "action": "get",
          "url": "http://crossben.ch",
          "ready_state": "interactive",
          "duration": "12s"
      })

  def test_parse_wait_default(self):
    config_dict = {"action": "wait", "duration": "12s"}
    action = WaitAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.WAIT)
    self.assertEqual(action.duration, dt.timedelta(seconds=12))
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = WaitAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_wait_missing_duration(self):
    with self.assertRaises(ValueError) as cm:
      WaitAction.parse_dict({"action": "wait"})
    self.assertIn("duration", str(cm.exception))

  def test_parse_scroll_default(self):
    config_dict = {"action": "scroll"}
    action = ScrollAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.SCROLL)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.duration, dt.timedelta(seconds=1))
    self.assertEqual(action.distance, 500)
    self.assertEqual(action.input_source, InputSource.JS)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = ScrollAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_scroll_all(self):
    config_dict = {
        "action": "scroll",
        "distance": "123",
        "timeout": "12s",
        "duration": "34s",
        "source": "js",
        "selector": "#button",
        "required": "true"
    }
    action = ScrollAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.SCROLL)
    self.assertEqual(action.timeout, dt.timedelta(seconds=12))
    self.assertEqual(action.duration, dt.timedelta(seconds=34))
    self.assertEqual(action.distance, 123)
    self.assertEqual(action.input_source, InputSource.JS)
    self.assertTrue(action.required)
    self.assertEqual(action.selector, "#button")
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = ScrollAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_scroll_invalid_source(self):
    config_dict = {
        "action": "scroll",
        "source": "invalid source",
    }

    with self.assertRaises(ValueError) as cm:
      ScrollAction.parse_dict(config_dict)

    self.assertIn("source", str(cm.exception))

  def test_parse_scroll_valid_but_unsupported_source(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({
          "action": "scroll",
          "source": "keyboard",
      })
    self.assertIn("source", str(cm.exception))

  def test_parse_scroll_required_missing_selector(self):
    config_dict = {
        "action": "scroll",
        "required": "true",
    }

    with self.assertRaises(ValueError) as cm:
      ScrollAction.parse_dict(config_dict)

    self.assertIn("required", str(cm.exception))

  def test_scroll_invalid_distance(self):
    with self.assertRaises(ValueError) as cm:
      ScrollAction.parse_dict({"action": "scroll", "distance": ""})
    self.assertIn("distance", str(cm.exception))
    with self.assertRaises(ValueError) as cm:
      ScrollAction.parse_dict({"action": "scroll", "distance": "0"})
    self.assertIn("distance", str(cm.exception))

  def test_parse_click_minimal_selector(self):
    config_dict = {"action": "click", "selector": "#button"}
    action = ClickAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.CLICK)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.input_source, InputSource.JS)
    self.assertEqual(action.selector, "#button")
    self.assertFalse(action.required)
    self.assertFalse(action.scroll_into_view)
    self.assertIsNone(action.coordinates)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = ClickAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_click_minimal_coordinates(self):
    config_dict = {"action": "click", "source": "touch", "x": 1, "y": 2}
    action = ClickAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.CLICK)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.input_source, InputSource.TOUCH)
    self.assertIsNone(action.selector)
    self.assertFalse(action.required)
    self.assertFalse(action.scroll_into_view)
    self.assertEqual(action.coordinates.x, 1)
    self.assertEqual(action.coordinates.y, 2)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = ClickAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_click_selector_all(self):
    config_dict = {
        "action": "click",
        "source": "js",
        "selector": "#button",
        "required": True,
        "scroll_into_view": True,
        "timeout": "12s"
    }
    action = ClickAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.CLICK)
    self.assertEqual(action.timeout, dt.timedelta(seconds=12))
    self.assertEqual(action.input_source, InputSource.JS)
    self.assertEqual(action.selector, "#button")
    self.assertTrue(action.required)
    self.assertTrue(action.scroll_into_view)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = ClickAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_click_invalid_source(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({
          "action": "click",
          "source": "invalid_source",
          "selector": "#button"
      })
    self.assertIn("source", str(cm.exception))

  def test_parse_click_valid_but_unsupported_source(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({
          "action": "click",
          "source": "keyboard",
          "selector": "#button"
      })
    self.assertIn("source", str(cm.exception))

  def test_parse_click_invalid_selector(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({"action": "click", "selector": ""})
    self.assertIn("selector", str(cm.exception))

  def test_parse_click_selector_and_coordinates(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({
          "action": "click",
          "source": "TOUCH",
          "selector": "#button",
          "x": 0,
          "y": 0
      })
    self.assertIn("either selector or coordinates", str(cm.exception))

  def test_parse_click_incomplete_coordinates(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({"action": "click", "source": "TOUCH", "x": 0})
    self.assertIn("Either selector or coordinates", str(cm.exception))

  def test_parse_click_coordinates_with_required(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({
          "action": "click",
          "source": "TOUCH",
          "x": 0,
          "y": 0,
          "required": "true"
      })
    self.assertIn("required", str(cm.exception))

  def test_parse_click_coordinates_with_scroll(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({
          "action": "click",
          "source": "TOUCH",
          "x": 0,
          "y": 0,
          "scroll_into_view": "true"
      })
    self.assertIn("scroll_into_view", str(cm.exception))

  def test_parse_click_coordinates_with_js(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({
          "action": "click",
          "source": "JS",
          "x": 0,
          "y": 0
      })
    self.assertIn("JS", str(cm.exception))

  def test_parse_click_missing_coordinates_and_selector(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({"action": "click", "source": "TOUCH"})
    self.assertIn("Either selector or coordinates", str(cm.exception))

  def test_parse_swipe(self):
    config_dict = {
        "action": "swipe",
        "startx": 100,
        "starty": 200,
        "endx": 110,
        "endy": 220,
        "duration": "12s"
    }
    action = SwipeAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.SWIPE)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.duration, dt.timedelta(seconds=12))
    self.assertEqual(action.start_x, 100)
    self.assertEqual(action.start_y, 200)
    self.assertEqual(action.end_x, 110)
    self.assertEqual(action.end_y, 220)
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = SwipeAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_text_input_minimal(self):
    config_dict = {
        "action": "text_input",
        "duration": "10s",
        "text": "some text"
    }
    action = TextInputAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.TEXT_INPUT)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.input_source, InputSource.JS)
    self.assertEqual(action.text, "some text")
    self.assertEqual(action.duration, dt.timedelta(seconds=10))
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = TextInputAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_text_input_non_default_source(self):
    config_dict = {
        "action": "text_input",
        "duration": "1s",
        "source": "keyboard",
        "text": "some text",
    }
    action = TextInputAction.parse_dict(config_dict)

    self.assertEqual(action.input_source, InputSource.KEYBOARD)

  def test_parse_text_input_invalid_source(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({
          "action": "text_input",
          "duration": "1s",
          "source": "invalid_source",
          "text": "some text",
      })
    self.assertIn("source", str(cm.exception))

  def test_parse_text_input_valid_but_unsupported_source(self):
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict({
          "action": "text_input",
          "duration": "1s",
          "source": "mouse",
          "text": "some text",
      })
    self.assertIn("source", str(cm.exception))

  def test_parse_text_input_negative_duration(self):
    config_dict = {
        "action": "text_input",
        "text": "some text",
        "duration": "-1s"
    }
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict(config_dict)
    self.assertIn("duration", str(cm.exception))

  def test_parse_text_input_missing_text(self):
    config_dict = {"action": "text_input", "duration": "1s"}
    with self.assertRaises(ValueError) as cm:
      ClickAction.parse_dict(config_dict)
    self.assertIn("text", str(cm.exception))

  def test_parse_wait_for_element(self):
    config_dict = {
        "action": "wait_for_element",
        "selector": "#button",
    }
    action = WaitForElementAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.WAIT_FOR_ELEMENT)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.selector, "#button")
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = WaitForElementAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_wait_for_element_timeout(self):
    config_dict = {
        "action": "wait_for_element",
        "selector": "#button",
        "timeout": "12s"
    }
    action = WaitForElementAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.WAIT_FOR_ELEMENT)
    self.assertEqual(action.timeout, dt.timedelta(seconds=12))
    self.assertEqual(action.selector, "#button")
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = WaitForElementAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_js_script(self):
    config_dict = {
        "action": "js",
        "script": "alert(1)",
    }
    action = JsAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.JS)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.script, "alert(1)")
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = JsAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_js_script_path(self):
    path = self.create_file("/foo/bar.js", contents="alert(2)")
    config_dict = {
        "action": "js",
        "script_path": str(path),
    }
    action = JsAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.JS)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.script, "alert(2)")
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = JsAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_js_script_path_with_replacements(self):
    path = self.create_file("/foo/bar.js", contents="alert($ALERT$)")
    config_dict = {
        "action": "js",
        "script_path": str(path),
        "replace": {
            "$ALERT$": "'something'"
        }
    }
    action = JsAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.JS)
    self.assertEqual(action.script, "alert('something')")
    action.validate()

    action_2 = JsAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_js_script_invalid(self):
    config_dict = {
        "action": "js",
        "script": "",
    }
    with self.assertRaises(ValueError) as cm:
      JsAction.parse_dict(config_dict)
    self.assertIn("script", str(cm.exception))


  def test_js_script_invalid_path(self):
    config_dict = {
        "action": "js",
        "script_path": "",
    }
    with self.assertRaises(ValueError) as cm:
      JsAction.parse_dict(config_dict)
    self.assertIn("script_path", str(cm.exception))

    config_dict = {
        "action": "js",
        "script_path": "/does/not/exist.js",
    }
    with self.assertRaises(ValueError) as cm:
      JsAction.parse_dict(config_dict)
    self.assertIn("script_path", str(cm.exception))


  def test_js_script_invalid_script_xor_path(self):
    path = self.create_file("/foo/bar.js", contents="alert(2)")
    config_dict = {
        "action": "js",
        "script": "alert(1)",
        "script_path": str(path),
    }
    with self.assertRaises(ValueError) as cm:
      JsAction.parse_dict(config_dict)
    self.assertIn("script_path", str(cm.exception))


  def test_js_script_invalid_replacements(self):
    path = self.create_file("/foo/bar.js", contents="alert(2)")
    config_dict = {
        "action": "js",
        "script_path": str(path),
        "replacements": {
            1: 1,
            "one": 1,
        }
    }
    with self.assertRaises(ValueError) as cm:
      JsAction.parse_dict(config_dict)
    self.assertIn("replacements", str(cm.exception))


  def test_inject_new_document_script_script(self):
    config_dict = {
        "action": "inject_new_document_script",
        "script": "alert(1)",
    }
    action = InjectNewDocumentScriptAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.INJECT_NEW_DOCUMENT_SCRIPT)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.script, "alert(1)")
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = InjectNewDocumentScriptAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_inject_new_document_script_script_path(self):
    path = self.create_file("/foo/bar.js", contents="alert(2)")
    config_dict = {
        "action": "inject_new_document_script",
        "script_path": str(path),
    }
    action = InjectNewDocumentScriptAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.INJECT_NEW_DOCUMENT_SCRIPT)
    self.assertEqual(action.timeout, ACTION_TIMEOUT)
    self.assertEqual(action.script, "alert(2)")
    self.assertTrue(action.has_timeout)
    action.validate()

    action_2 = InjectNewDocumentScriptAction.parse_dict(action.to_json())
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
    action = InjectNewDocumentScriptAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.INJECT_NEW_DOCUMENT_SCRIPT)
    self.assertEqual(action.script, "alert('something')")
    action.validate()

    action_2 = InjectNewDocumentScriptAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_inject_new_document_script_invalid(self):
    config_dict = {
        "action": "inject_new_document_script",
        "script": "",
    }
    with self.assertRaises(ValueError) as cm:
      InjectNewDocumentScriptAction.parse_dict(config_dict)
    self.assertIn("script", str(cm.exception))


  def test_inject_new_document_script_invalid_path(self):
    config_dict = {
        "action": "inject_new_document_script",
        "script_path": "",
    }
    with self.assertRaises(ValueError) as cm:
      InjectNewDocumentScriptAction.parse_dict(config_dict)
    self.assertIn("script_path", str(cm.exception))

    config_dict = {
        "action": "inject_new_document_script",
        "script_path": "/does/not/exist.js",
    }
    with self.assertRaises(ValueError) as cm:
      InjectNewDocumentScriptAction.parse_dict(config_dict)
    self.assertIn("script_path", str(cm.exception))


  def test_inject_new_document_script_invalid_script_xor_path(self):
    path = self.create_file("/foo/bar.js", contents="alert(2)")
    config_dict = {
        "action": "inject_new_document_script",
        "script": "alert(1)",
        "script_path": str(path),
    }
    with self.assertRaises(ValueError) as cm:
      InjectNewDocumentScriptAction.parse_dict(config_dict)
    self.assertIn("script_path", str(cm.exception))


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
      InjectNewDocumentScriptAction.parse_dict(config_dict)
    self.assertIn("replacements", str(cm.exception))


  def test_parse_switch_tab_all_args(self):
    config_dict = {
        "action": "switch_tab",
        "tab_index": 17,
        "title": "^Example.*",
        "url": "http(s)?://example.com"
    }
    action = SwitchTabAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.SWITCH_TAB)
    self.assertEqual(action.tab_index, 17)
    self.assertEqual(action.title.pattern, "^Example.*")
    self.assertEqual(action.url.pattern, "http(s)?://example.com")
    action.validate()

    action_2 = SwitchTabAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_switch_tab_no_args(self):
    config_dict = {
        "action": "switch_tab",
    }
    action = SwitchTabAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.SWITCH_TAB)
    self.assertEqual(action.tab_index, None)
    self.assertEqual(action.title, None)
    self.assertEqual(action.url, None)
    action.validate()

    action_2 = SwitchTabAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_wait_for_ready_state(self):
    config_dict = {
        "action": "wait_for_ready_state",
    }
    action = WaitForReadyStateAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.WAIT_FOR_READY_STATE)
    self.assertEqual(action.ready_state, ReadyState.COMPLETE)
    action.validate()

    action_2 = WaitForReadyStateAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

  def test_parse_wait_for_ready_state_interactive(self):
    config_dict = {
        "action": "wait_for_ready_state",
        "ready_state": "interactive",
    }
    action = WaitForReadyStateAction.parse_dict(config_dict)

    self.assertEqual(action.TYPE, ActionType.WAIT_FOR_READY_STATE)
    self.assertEqual(action.ready_state, ReadyState.INTERACTIVE)
    action.validate()

    action_2 = WaitForReadyStateAction.parse_dict(action.to_json())
    self.assertEqual(action, action_2)
    action_2.validate()

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
