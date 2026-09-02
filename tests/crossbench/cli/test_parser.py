# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest

from crossbench.cli.parser import CBArgumentParser, CBNamespace
from tests import test_helper


class CBNamespaceTestCase(unittest.TestCase):

  def test_init(self) -> None:
    ns = CBNamespace(foo="bar", num=42)
    self.assertEqual(ns.foo, "bar")
    self.assertEqual(ns.num, 42)

  def test_modify_before_freeze(self) -> None:
    ns = CBNamespace(foo="bar")
    ns.foo = "baz"
    self.assertEqual(ns.foo, "baz")
    ns.new_attr = 100
    self.assertEqual(ns.new_attr, 100)
    del ns.foo
    self.assertNotIn("foo", vars(ns))

  def test_freeze_blocks_mutation(self) -> None:
    ns = CBNamespace(foo="bar", num=42)
    frozen_ns = ns.freeze()
    self.assertIs(frozen_ns, ns)

    with self.assertRaisesRegex(TypeError, "Cannot modify immutable"):
      ns.foo = "baz"
    with self.assertRaisesRegex(TypeError, "Cannot modify immutable"):
      ns.new_attr = 100
    with self.assertRaisesRegex(TypeError, "Cannot delete attribute"):
      del ns.foo

    self.assertEqual(ns.foo, "bar")
    self.assertEqual(ns.num, 42)

  def test_freeze_is_idempotent(self) -> None:
    ns = CBNamespace(foo="bar")
    ns.freeze()
    with self.assertRaises(TypeError):
      ns.foo = "baz"
    ns.freeze()
    with self.assertRaises(TypeError):
      ns.foo = "baz"

  def test_nested_freeze(self) -> None:
    nested = CBNamespace(inner="value")
    parent = CBNamespace(child=nested, name="parent")
    nested.inner = "value2"
    self.assertEqual(nested.inner, "value2")

    parent.freeze()
    with self.assertRaises(TypeError):
      parent.name = "changed"
    with self.assertRaises(TypeError):
      nested.inner = "changed"


class CBArgumentParserTestCase(unittest.TestCase):

  def test_parse_args_returns_crossbench_namespace(self) -> None:
    parser = CBArgumentParser()
    parser.add_argument("--test-flag", default="default_value")
    args = parser.parse_args(["--test-flag=custom"])
    self.assertIsInstance(args, CBNamespace)
    self.assertEqual(args.test_flag, "custom")

  def test_parse_known_args_returns_crossbench_namespace(self) -> None:
    parser = CBArgumentParser()
    parser.add_argument("--flag", default="a")
    args, unprocessed = parser.parse_known_args(["--flag=b", "extra"])
    self.assertIsInstance(args, CBNamespace)
    self.assertEqual(args.flag, "b")
    self.assertEqual(unprocessed, ["extra"])


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
