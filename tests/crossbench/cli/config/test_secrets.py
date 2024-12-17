# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json

import hjson
from immutabledict import immutabledict

from crossbench.cli.config.secrets import Secret, SecretsConfig, SecretType
from tests.crossbench.cli.config.base import BaseConfigTestCase


class SecretsConfigTestCase(BaseConfigTestCase):

  def test_parse_empty(self):
    secrets = SecretsConfig.parse({})
    self.assertEqual(secrets.secrets, immutabledict())

  def test_parse_google(self):
    secrets = SecretsConfig.parse(
        {"google": {
            "password": "pw",
            "account": "user@test.com"
        }})
    self.assertEqual(secrets.secrets[SecretType.GOOGLE],
                     Secret(SecretType.GOOGLE, "user@test.com", "pw"))
    secrets = SecretsConfig.parse(
        {"google": {
            "user": "user@test.com",
            "password": ""
        }})
    self.assertEqual(secrets.secrets[SecretType.GOOGLE],
                     Secret(SecretType.GOOGLE, "user@test.com", ""))

  def test_equal_empty(self):
    secrets_1 = SecretsConfig.parse({})
    secrets_2 = SecretsConfig.parse({})
    self.assertEqual(secrets_1, secrets_1)
    self.assertEqual(secrets_1, secrets_2)
    self.assertEqual(secrets_2, secrets_1)

  def test_equal_single_item(self):
    secrets_empty = SecretsConfig.parse({})
    secrets_1 = SecretsConfig.parse(
        {"google": {
            "password": "pw",
            "account": "user@test.com"
        }})
    secrets_2 = SecretsConfig.parse(
        {"google": {
            "password": "pw",
            "account": "user@test.com"
        }})
    self.assertEqual(secrets_1, secrets_1)
    self.assertEqual(secrets_1, secrets_2)
    self.assertEqual(secrets_2, secrets_1)
    self.assertNotEqual(secrets_1, secrets_empty)
    self.assertNotEqual(secrets_empty, secrets_1)
    self.assertNotEqual(secrets_2, secrets_empty)
    self.assertNotEqual(secrets_empty, secrets_2)

  def test_not_equal_single_item(self):
    secrets_1 = SecretsConfig.parse(
        {"google": {
            "password": "pw",
            "account": "user@test.com"
        }})
    secrets_2 = SecretsConfig.parse(
        {"google": {
            "password": "PASSWORD",
            "account": "user@test.com"
        }})
    self.assertNotEqual(secrets_1, secrets_2)

  def test_parse_inline_hjson(self):
    config_data = {"google": {"password": "pw", "account": "user@test.com"}}
    secrets_inline_hjson = SecretsConfig.parse(hjson.dumps(config_data))
    secrets_inline_json = SecretsConfig.parse(json.dumps(config_data))
    secrets_dict = SecretsConfig.parse(config_data)
    self.assertEqual(secrets_inline_hjson, secrets_dict)
    self.assertEqual(secrets_inline_json, secrets_dict)
