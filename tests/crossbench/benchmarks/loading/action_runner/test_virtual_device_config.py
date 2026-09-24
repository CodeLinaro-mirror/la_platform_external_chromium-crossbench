# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest

from crossbench.action_runner.virtual_device.all import VIRTUAL_DEVICES_TUPLE
from crossbench.action_runner.virtual_device.keyboard import \
    KeyboardVirtualDeviceConfig
from crossbench.action_runner.virtual_device.touchscreen import \
    DEFAULT_TOUCH_POLLING_RATE_HZ, TouchscreenVirtualDeviceConfig
from crossbench.action_runner.virtual_device.virtual_device_config import \
    VIRTUAL_DEVICES, VirtualDeviceConfig
from crossbench.action_runner.virtual_device.virtual_device_type import \
    VirtualDeviceType
from tests import test_helper


class VirtualDeviceConfigTestCase(unittest.TestCase):

  def test_parse_keyboard(self) -> None:
    config_dict = {
        "type": "keyboard",
        "name": "default_keyboard",
    }
    device = VirtualDeviceConfig.parse_dict(config_dict)
    self.assertIsInstance(device, KeyboardVirtualDeviceConfig)
    assert isinstance(device, KeyboardVirtualDeviceConfig)
    self.assertEqual(device.name, "default_keyboard")
    self.assertEqual(device.device_type, VirtualDeviceType.KEYBOARD)

    device_2 = VirtualDeviceConfig.parse_dict(device.to_json())
    self.assertEqual(device, device_2)


  def test_all_virtual_devices(self) -> None:
    self.assertTrue(VIRTUAL_DEVICES_TUPLE)
    self.assertEqual(len(VIRTUAL_DEVICES_TUPLE), len(VirtualDeviceType))
    self.assertEqual(len(VIRTUAL_DEVICES), len(VirtualDeviceType))
    self.assertEqual(set(VIRTUAL_DEVICES.keys()), set(VirtualDeviceType))
    self.assertEqual(
        len(VIRTUAL_DEVICES_TUPLE), len(set(VIRTUAL_DEVICES_TUPLE)))

  def test_parse_touchscreen_defaults(self) -> None:
    config_dict = {
        "type": "touchscreen",
        "name": "default_touchscreen",
    }
    device = VirtualDeviceConfig.parse_dict(config_dict)
    self.assertIsInstance(device, TouchscreenVirtualDeviceConfig)
    assert isinstance(device, TouchscreenVirtualDeviceConfig)
    self.assertEqual(device.name, "default_touchscreen")
    self.assertEqual(device.device_type, VirtualDeviceType.TOUCHSCREEN)
    self.assertIsNone(device.width)
    self.assertIsNone(device.height)
    self.assertEqual(device.polling_rate_hz, DEFAULT_TOUCH_POLLING_RATE_HZ)

    device_2 = VirtualDeviceConfig.parse_dict(device.to_json())
    self.assertEqual(device, device_2)

  def test_parse_touchscreen_explicit(self) -> None:
    config_dict = {
        "type": "touchscreen",
        "name": "custom_touchscreen",
        "width": 1080,
        "height": 2400,
        "polling_rate_hz": 240,
    }
    device = VirtualDeviceConfig.parse_dict(config_dict)
    self.assertIsInstance(device, TouchscreenVirtualDeviceConfig)
    assert isinstance(device, TouchscreenVirtualDeviceConfig)
    self.assertEqual(device.name, "custom_touchscreen")
    self.assertEqual(device.device_type, VirtualDeviceType.TOUCHSCREEN)
    self.assertEqual(device.width, 1080)
    self.assertEqual(device.height, 2400)
    self.assertEqual(device.polling_rate_hz, 240)

    device_2 = VirtualDeviceConfig.parse_dict(device.to_json())
    self.assertEqual(device, device_2)

  def test_parse_touchscreen_device_type_alias(self) -> None:
    config_dict = {
        "device_type": "touchscreen",
        "name": "ts",
        "width": 100,
        "height": 200,
    }
    device = VirtualDeviceConfig.parse_dict(config_dict)
    self.assertIsInstance(device, TouchscreenVirtualDeviceConfig)
    assert isinstance(device, TouchscreenVirtualDeviceConfig)
    self.assertEqual(device.width, 100)
    self.assertEqual(device.height, 200)

  def test_virtual_device_type_lookup(self) -> None:
    self.assertTrue(VIRTUAL_DEVICES_TUPLE)
    for device_type in VirtualDeviceType:
      device_cls = VIRTUAL_DEVICES[device_type]
      self.assertTrue(issubclass(device_cls, VirtualDeviceConfig))
      self.assertIs(device_cls.config_parser().cls, device_cls)
      self.assertIs(
          device_cls.config_parser(), device_cls.config_parser(),
          f"{device_cls}: missing "
          "@functools.lru_cache decorator on config_parser() method")
      self.assertIs(device_cls.TYPE, device_type)

  def test_parse_empty_name(self) -> None:
    with self.assertRaises(ValueError):
      VirtualDeviceConfig.parse_dict({
          "type": "keyboard",
          "name": "",
      })

  def test_parse_touchscreen_invalid_dimensions(self) -> None:
    with self.assertRaises(ValueError):
      VirtualDeviceConfig.parse_dict({
          "type": "touchscreen",
          "name": "ts",
          "width": 0,
          "height": 100,
      })
    with self.assertRaises(ValueError):
      VirtualDeviceConfig.parse_dict({
          "type": "touchscreen",
          "name": "ts",
          "width": -10,
          "height": 100,
      })
    with self.assertRaises(ValueError):
      VirtualDeviceConfig.parse_dict({
          "type": "touchscreen",
          "name": "ts",
          "width": 100,
          "height": 0,
      })
    with self.assertRaises(ValueError):
      VirtualDeviceConfig.parse_dict({
          "type": "touchscreen",
          "name": "ts",
          "width": 100,
      })
    with self.assertRaises(ValueError):
      VirtualDeviceConfig.parse_dict({
          "type": "touchscreen",
          "name": "ts",
          "height": 100,
      })

  def test_parse_touchscreen_polling_rate_aliases(self) -> None:
    for field_name in ("polling_rate", "rate", "frequency"):
      config_dict = {
          "type": "touchscreen",
          "name": "ts",
          field_name: 60,
      }
      device = VirtualDeviceConfig.parse_dict(config_dict)
      self.assertIsInstance(device, TouchscreenVirtualDeviceConfig)
      assert isinstance(device, TouchscreenVirtualDeviceConfig)
      self.assertEqual(device.polling_rate_hz, 60)

  def test_parse_touchscreen_invalid_polling_rate(self) -> None:
    with self.assertRaises(ValueError):
      VirtualDeviceConfig.parse_dict({
          "type": "touchscreen",
          "name": "ts",
          "polling_rate_hz": 0,
      })
    with self.assertRaises(ValueError):
      VirtualDeviceConfig.parse_dict({
          "type": "touchscreen",
          "name": "ts",
          "polling_rate_hz": -10,
      })

  def test_direct_instantiation_validation(self) -> None:
    with self.assertRaises(ValueError):
      KeyboardVirtualDeviceConfig(name="")
    with self.assertRaises(ValueError):
      TouchscreenVirtualDeviceConfig(name="ts", width=-1, height=100)
    with self.assertRaises(ValueError):
      TouchscreenVirtualDeviceConfig(name="ts", width=100, height=None)
    with self.assertRaises(ValueError):
      TouchscreenVirtualDeviceConfig(name="ts", polling_rate_hz=0)
    with self.assertRaises(ValueError):
      TouchscreenVirtualDeviceConfig(name="ts", polling_rate_hz=-1)

  def test_parse_invalid_type(self) -> None:
    with self.assertRaises(ValueError):
      VirtualDeviceConfig.parse_dict({
          "type": "invalid_type",
          "name": "dev",
      })

  def test_parse_missing_name(self) -> None:
    with self.assertRaises(ValueError):
      VirtualDeviceConfig.parse_dict({"type": "keyboard"})

  def test_parse_str_unsupported(self) -> None:
    with self.assertRaises(ValueError):
      VirtualDeviceConfig.parse_str("keyboard")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
