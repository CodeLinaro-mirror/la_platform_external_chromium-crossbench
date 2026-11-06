# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt
import json
import unittest
from unittest.mock import MagicMock

from google.genai import types

from crossbench.action_runner.action.wait import WaitAction
from crossbench.action_runner.llm_client import AgentTurnResponse, \
    LlmConversationClient
from crossbench.config import ConfigError
from tests import test_helper


class AgentTurnResponseTestCase(unittest.TestCase):

  def test_parse_valid_actions(self) -> None:
    payload = {
        "observation": "Page loaded",
        "thought": "Wait 10ms",
        "done": False,
        "anomaly": "UI stall",
        "actions": [{
            "action": "wait",
            "duration": "10ms",
        }],
    }
    turn = AgentTurnResponse.parse(payload)
    self.assertEqual(turn.observation, "Page loaded")
    self.assertEqual(turn.thought, "Wait 10ms")
    self.assertFalse(turn.done)
    self.assertEqual(turn.anomaly, "UI stall")
    self.assertEqual(len(turn.actions), 1)
    self.assertIsInstance(turn.actions[0], WaitAction)
    assert isinstance(turn.actions[0], WaitAction)
    self.assertEqual(turn.actions[0].duration, dt.timedelta(milliseconds=10))

    turn_from_json = AgentTurnResponse.parse(json.dumps(payload))
    self.assertEqual(turn_from_json.observation, turn.observation)
    self.assertEqual(len(turn_from_json.actions), 1)

  def test_parse_non_json_string_raises(self) -> None:
    with self.assertRaises(argparse.ArgumentTypeError):
      AgentTurnResponse.parse("not a json object")
    with self.assertRaises(ConfigError):
      AgentTurnResponse.parse_str("not a json object")

  def test_parse_invalid_action_raises(self) -> None:
    with self.assertRaises(argparse.ArgumentTypeError):
      AgentTurnResponse.parse({
          "observation": "Page loaded",
          "thought": "Invalid action",
          "actions": [{
              "action": "non_existent_action",
          }],
      })


class LlmConversationClientTestCase(unittest.TestCase):

  def test_invalid_init_arguments_raise(self) -> None:
    with self.assertRaises(argparse.ArgumentTypeError):
      LlmConversationClient(
          model="",
          system_instruction="Test",
          temperature=1.0,
      )
    with self.assertRaises(argparse.ArgumentTypeError):
      LlmConversationClient(
          model="gemini-2.5-flash",
          system_instruction="",
          temperature=1.0,
      )
    with self.assertRaises(argparse.ArgumentTypeError):
      LlmConversationClient(
          model="gemini-2.5-flash",
          system_instruction="Test",
          temperature=3.0,
      )
    with self.assertRaises(argparse.ArgumentTypeError):
      LlmConversationClient(
          model="gemini-2.5-flash",
          system_instruction="Test",
          temperature=1.0,
          api_key="",
      )
    with self.assertRaises(argparse.ArgumentTypeError):
      LlmConversationClient(
          model="gemini-2.5-flash",
          system_instruction="Test",
          temperature=1.0,
          max_history_screenshots=-1,
      )

  def test_send_turn_uses_chat_session_and_parses_response(self) -> None:
    mock_genai_client = MagicMock()
    mock_chat = MagicMock()
    mock_genai_client.chats.create.return_value = mock_chat

    resp = MagicMock()
    resp.text = json.dumps({
        "observation": "Obs 1",
        "thought": "Thought 1",
        "done": False,
        "request_trace_snapshot": False,
        "anomaly_reason": "",
        "actions": [{
            "action": "wait",
            "duration": "10ms",
        }],
    })
    mock_chat.send_message.return_value = resp

    client = LlmConversationClient(
        model="gemini-2.5-flash",
        system_instruction="Test instruction",
        temperature=1.2,
        api_key="test-key",
        genai_client=mock_genai_client,
    )

    turn_1 = client.send_turn("Step 1", b"png_bytes_1")
    turn_2 = client.send_turn("Step 2")

    mock_genai_client.chats.create.assert_called_once()
    self.assertEqual(mock_chat.send_message.call_count, 2)
    self.assertEqual(len(mock_chat.send_message.call_args_list[0].args[0]), 2)
    self.assertEqual(len(mock_chat.send_message.call_args_list[1].args[0]), 1)
    self.assertEqual(turn_1.observation, "Obs 1")
    self.assertEqual(turn_2.observation, "Obs 1")
    self.assertEqual(len(turn_1.actions), 1)
    self.assertIsInstance(turn_1.actions[0], WaitAction)

  def test_send_turn_empty_response_raises(self) -> None:
    mock_genai_client = MagicMock()
    mock_chat = MagicMock()
    mock_genai_client.chats.create.return_value = mock_chat
    resp = MagicMock()
    resp.text = ""
    mock_chat.send_message.return_value = resp

    client = LlmConversationClient(
        model="gemini-2.5-flash",
        system_instruction="Test",
        temperature=1.0,
        genai_client=mock_genai_client,
    )
    with self.assertRaisesRegex(RuntimeError, "empty response text"):
      client.send_turn("Step 1")

  def test_prune_prompt_history_data_caps_old_screenshots(self) -> None:
    mock_genai_client = MagicMock()
    mock_chat = MagicMock()
    mock_genai_client.chats.create.return_value = mock_chat

    history = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="Step 1"),
                types.Part.from_bytes(data=b"png_1", mime_type="image/png"),
            ],
        ),
        types.Content(
            role="model",
            parts=[types.Part.from_text(text="{}")],
        ),
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="Step 2"),
                types.Part.from_bytes(data=b"png_2", mime_type="image/png"),
            ],
        ),
        types.Content(
            role="model",
            parts=[types.Part.from_text(text="{}")],
        ),
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="Step 3"),
                types.Part.from_bytes(data=b"png_3", mime_type="image/png"),
            ],
        ),
    ]
    mock_chat.get_history.return_value = history

    resp = MagicMock()
    resp.text = json.dumps({
        "observation": "Obs",
        "thought": "Thought",
        "done": True,
        "actions": [],
    })
    mock_chat.send_message.return_value = resp

    client = LlmConversationClient(
        model="gemini-3.8-flash",
        system_instruction="Test",
        temperature=1.0,
        genai_client=mock_genai_client,
        max_history_screenshots=2,
    )
    client.send_turn("Step 4", b"png_4")

    parts_0 = history[0].parts
    parts_2 = history[2].parts
    parts_4 = history[4].parts
    assert parts_0 is not None
    assert parts_2 is not None
    assert parts_4 is not None
    self.assertEqual(len(parts_0), 1)
    self.assertEqual(parts_0[0].text, "Step 1")
    self.assertEqual(len(parts_2), 2)
    self.assertEqual(len(parts_4), 2)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
