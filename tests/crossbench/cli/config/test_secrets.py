# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import json
import re
import unittest

import hjson

from crossbench.cli.config.secrets import CycledUsernamePassword, \
    GoogleUsernamePassword, Secrets, SecretsMergeError, ServiceAccount, \
    UsernamePassword
from tests import test_helper
from tests.crossbench.cli.config.base import BaseConfigTestCase


class SecretsConfigTestCase(BaseConfigTestCase):

  def bond_config_dict(self):
    return {
        "bond": {
            "type": "service_account",
            "project_id": "my-project",
            "private_key_id": "0BADC0DE",
            "private_key": "-----BEGIN PRIVATE KEY-----\n...",
            "client_email": "name@example.com",
            "client_id": "7",
            "auth_uri": "https://example.com/oauth",
            "token_uri": "https://example.com/token",
            "auth_provider_x509_cert_url": "https://example.com/certs",
            "client_x509_cert_url": "https://example.com/x509/my-project.cert",
            "universe_domain": "example.com",
        }
    }

  def test_parse_empty(self):
    secrets = Secrets.parse({})
    self.assertEqual(secrets.google, None)

  def test_parse_interactive(self):
    secrets = Secrets.parse({"google": "interactive"})
    self.assertTrue(secrets.google.is_interactive)

  def test_parse_google(self):
    secrets = Secrets.parse(
        {"google": {
            "password": "pw",
            "account": "user@test.com"
        }})
    self.assertEqual(secrets.google,
                     GoogleUsernamePassword("user@test.com", "pw"))
    self.assertFalse(secrets.google.is_interactive)
    secrets = Secrets.parse(
        {"google": {
            "user": "user@test.com",
            "password": ""
        }})
    self.assertEqual(secrets.google,
                     GoogleUsernamePassword("user@test.com", ""))

  def test_parse_bond(self):
    secrets = Secrets.parse(self.bond_config_dict())
    self.assertEqual(
        secrets.bond,
        ServiceAccount(
            type="service_account",
            project_id="my-project",
            private_key_id="0BADC0DE",
            private_key="-----BEGIN PRIVATE KEY-----\n...",
            client_email="name@example.com",
            client_id="7",
            auth_uri="https://example.com/oauth",
            token_uri="https://example.com/token",
            auth_provider_x509_cert_url="https://example.com/certs",
            client_x509_cert_url="https://example.com/x509/my-project.cert",
            universe_domain="example.com",
        ))
    self.assertFalse(secrets.bond.is_interactive)

  def test_equal_empty(self):
    secrets_1 = Secrets.parse({})
    secrets_2 = Secrets.parse({})
    self.assertEqual(secrets_1, secrets_1)
    self.assertEqual(secrets_1, secrets_2)
    self.assertEqual(secrets_2, secrets_1)

  def test_equal_single_item(self):
    secrets_empty = Secrets.parse({})
    secrets_1 = Secrets.parse(
        {"google": {
            "password": "pw",
            "account": "user@test.com"
        }})
    secrets_2 = Secrets.parse(
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
    secrets_1 = Secrets.parse(
        {"google": {
            "password": "pw",
            "account": "user@test.com"
        }})
    secrets_2 = Secrets.parse(
        {"google": {
            "password": "PASSWORD",
            "account": "user@test.com"
        }})
    self.assertNotEqual(secrets_1, secrets_2)

  def test_equal_bond_item(self):
    secrets_empty = Secrets.parse({})
    bond_config = self.bond_config_dict()
    secrets_1 = Secrets.parse(bond_config)
    secrets_2 = Secrets.parse(bond_config)
    self.assertEqual(secrets_1, secrets_1)
    self.assertEqual(secrets_1, secrets_2)
    self.assertEqual(secrets_2, secrets_1)
    self.assertNotEqual(secrets_1, secrets_empty)
    self.assertNotEqual(secrets_empty, secrets_1)
    self.assertNotEqual(secrets_2, secrets_empty)
    self.assertNotEqual(secrets_empty, secrets_2)

  def test_not_equal_bond_item(self):
    bond_config_1 = self.bond_config_dict()
    bond_config_2 = self.bond_config_dict()
    bond_config_2["bond"]["private_key_id"] = "1BADBEEF"
    secrets_1 = Secrets.parse(bond_config_1)
    secrets_2 = Secrets.parse(bond_config_2)
    self.assertNotEqual(secrets_1, secrets_2)

  def test_parse_inline_hjson(self):
    config_data = {"google": {"password": "pw", "account": "user@test.com"}}
    secrets_inline_hjson = Secrets.parse(hjson.dumps(config_data))
    secrets_inline_json = Secrets.parse(json.dumps(config_data))
    secrets_dict = Secrets.parse(config_data)
    self.assertEqual(secrets_inline_hjson, secrets_dict)
    self.assertEqual(secrets_inline_json, secrets_dict)

  def test_merge(self):
    secrets_1 = Secrets.parse(
        {"google": {
            "password": "pw",
            "account": "user1@test.com"
        }})
    secrets_2 = Secrets.parse(
        {"google": {
            "password": "PASSWORD",
            "account": "user2@test.com"
        }})
    merged = secrets_1.merge(fallback=secrets_2)
    self.assertEqual(secrets_1, merged)

  def test_merge_strict(self):
    secrets_1 = Secrets.parse(
        {"google": {
            "password": "pw",
            "account": "user1@test.com"
        }})
    secrets_2 = Secrets.parse(
        {"google": {
            "password": "PASSWORD",
            "account": "user2@test.com"
        }})
    merged = secrets_1.merge(fallback=secrets_1, strict=True)
    self.assertEqual(secrets_1, merged)

    with self.assertRaisesRegex(SecretsMergeError,
                                "Conflicting Google secrets"):
      secrets_1.merge(fallback=secrets_2, strict=True)

  def test_cycled_account_default(self):
    cycled_account = CycledUsernamePassword.parse({
        "username": "user@user.com",
        "password": "password"
    })

    self.assertEqual(cycled_account.username, "user@user.com")
    self.assertEqual(cycled_account.password, "password")

  def test_cycled_account_explicit_no_cycle(self):
    cycled_account = CycledUsernamePassword.parse({
        "username": "user@user.com",
        "password": "password",
        "use_range": False,
        "start": 0,
        "end": 10,
    })

    self.assertEqual(cycled_account.username, "user@user.com")
    self.assertEqual(cycled_account.password, "password")

  def test_cycled_account_explicit_cycle(self):
    cycled_account = CycledUsernamePassword.parse({
        "username": "user%d@user.com",
        "password": "password",
        "use_range": True,
        "start": 0,
        "end": 9,
    })

    self.assertTrue(re.match(r"user\d@user.com", cycled_account.username))
    self.assertEqual(cycled_account.password, "password")


class UsernamePasswordTestCase(unittest.TestCase):

  def test_parse_interactive(self):
    secret = UsernamePassword.parse("interactive")
    self.assertTrue(secret.is_interactive)

  def test_google(self):
    secret = GoogleUsernamePassword("user@test.com", "pw")
    self.assertFalse(secret.is_interactive)
    self.assertEqual(secret.username, "user@test.com")
    self.assertEqual(secret.password, "pw")

  def test_equality(self):
    secret_1 = GoogleUsernamePassword("user@test.com", "pw")
    self.assertEqual(secret_1, secret_1)

    secret_2 = GoogleUsernamePassword("user@test.com", "pw")
    self.assertEqual(secret_1, secret_2)

    secret_3 = GoogleUsernamePassword("other@test.com", "pw")
    self.assertNotEqual(secret_1, secret_3)


class ServiceAccountTestCase(unittest.TestCase):

  def test_equality(self):
    account_1 = ServiceAccount(
        type="service_account",
        project_id="my-project",
        private_key_id="0BADC0DE",
        private_key="-----BEGIN PRIVATE KEY-----\n...",
        client_email="name@example.com",
        client_id="7",
        auth_uri="https://example.com/oauth",
        token_uri="https://example.com/token",
        auth_provider_x509_cert_url="https://example.com/certs",
        client_x509_cert_url="https://example.com/x509/my-project.cert",
        universe_domain="example.com",
    )
    self.assertEqual(account_1, account_1)

    account_2 = ServiceAccount(
        type="service_account",
        project_id="my-project",
        private_key_id="0BADC0DE",
        private_key="-----BEGIN PRIVATE KEY-----\n...",
        client_email="name@example.com",
        client_id="7",
        auth_uri="https://example.com/oauth",
        token_uri="https://example.com/token",
        auth_provider_x509_cert_url="https://example.com/certs",
        client_x509_cert_url="https://example.com/x509/my-project.cert",
        universe_domain="example.com",
    )
    self.assertEqual(account_1, account_2)

    account_3 = ServiceAccount(
        type="service_account_other",
        project_id="my-project",
        private_key_id="0BADC0DE",
        private_key="-----BEGIN PRIVATE KEY-----\n...",
        client_email="name@example.com",
        client_id="7",
        auth_uri="https://example.com/oauth",
        token_uri="https://example.com/token",
        auth_provider_x509_cert_url="https://example.com/certs",
        client_x509_cert_url="https://example.com/x509/my-project.cert",
        universe_domain="example.com",
    )
    self.assertNotEqual(account_1, account_3)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
