# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import json

from crossbench import path as pth
from crossbench.cli.config.network import (NetworkConfig, NetworkSpeedConfig,
                                           NetworkSpeedPreset, NetworkType)
from tests import test_helper
from tests.crossbench.cli.config.base import BaseConfigTestCase


class NetworkSpeedConfigTestCase(BaseConfigTestCase):

  def test_parse_invalid(self):
    for invalid in ("", None, "---"):
      with self.subTest(invalid=invalid):
        with self.assertRaises(argparse.ArgumentTypeError):
          NetworkSpeedConfig.parse(invalid)
        with self.assertRaises(argparse.ArgumentTypeError):
          NetworkSpeedConfig.parse_str(str(invalid))
      with self.assertRaises(argparse.ArgumentTypeError) as cm:
        NetworkSpeedConfig.parse("not a speed preset value")
      self.assertIn("choices are", str(cm.exception).lower())

  def test_parse_default(self):
    config = NetworkSpeedConfig.parse("default")
    self.assertEqual(config, NetworkSpeedConfig.default())

  def test_default(self):
    config = NetworkSpeedConfig.default()
    self.assertIsNone(config.rtt_ms)
    self.assertIsNone(config.in_kbps)
    self.assertIsNone(config.out_kbps)
    self.assertIsNone(config.window)

  def test_parse_speed_preset(self):
    config = NetworkSpeedConfig.parse("4G")
    self.assertNotEqual(config, NetworkSpeedConfig.default())

    for preset in NetworkSpeedPreset:  # pytype: disable=missing-parameter
      config = NetworkSpeedConfig.parse(str(preset))
      self.assertEqual(config, NetworkSpeedConfig.parse_preset(preset))

  def test_parse_invalid_preset(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkSpeedConfig.parse("1xx4")
    self.assertIn("1xx4", str(cm.exception))
    self.assertIn("Choices are", str(cm.exception))

  def test_parse_dict(self):
    config = NetworkSpeedConfig.parse({
        "rtt_ms": 100,
        "in_kbps": 200,
        "out_kbps": 300,
        "window": 400
    })
    self.assertIsNone(config.ts_proxy)
    self.assertEqual(config.rtt_ms, 100)
    self.assertEqual(config.in_kbps, 200)
    self.assertEqual(config.out_kbps, 300)
    self.assertEqual(config.window, 400)

  def test_parse_invalid_dict(self):
    for int_property in ("rtt_ms", "in_kbps", "out_kbps", "window"):
      with self.subTest(config_property=int_property):
        with self.assertRaises(argparse.ArgumentTypeError) as cm:
          _ = NetworkSpeedConfig.parse({int_property: -100})
        self.assertIn(int_property, str(cm.exception))

  def test_parse_ts_proxy_path(self):
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      _ = NetworkSpeedConfig.parse({"ts_proxy": "/some/random/path"})
    self.assertIn("ts_proxy", str(cm.exception))
    ts_proxy = pth.LocalPath("/python/ts_proxy.py")
    self.fs.create_file(ts_proxy, st_size=100)
    config = NetworkSpeedConfig.parse({"ts_proxy": str(ts_proxy)})
    self.assertEqual(config.ts_proxy, ts_proxy)


class NetworkConfigTestCase(BaseConfigTestCase):

  def test_parse_invalid(self):
    for invalid in ("", None, "---", "something"):
      with self.assertRaises(argparse.ArgumentTypeError):
        NetworkConfig.parse(invalid)
      with self.assertRaises(argparse.ArgumentTypeError):
        NetworkConfig.parse_str(str(invalid))

  def test_parse_default(self):
    config = NetworkConfig.parse("default")
    self.assertEqual(config, NetworkConfig.default())

  def test_default(self):
    config = NetworkConfig.default()
    self.assertEqual(config.type, NetworkType.LIVE)
    self.assertEqual(config.speed, NetworkSpeedConfig.default())
    config_1 = NetworkConfig.parse({})
    self.assertEqual(config, config_1)
    config_2 = NetworkConfig.parse("{}")
    self.assertEqual(config, config_2)

  def test_parse_replay_archive_invalid(self):
    path = pth.LocalPath("/foo/bar/wprgo.archive")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkConfig.parse(str(path))
    message = str(cm.exception)
    self.assertIn("wpr.go archive", message)
    self.assertIn("exist", message)

    self.fs.create_file(path)
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkConfig.parse(str(path))
    message = str(cm.exception)
    self.assertIn("wpr.go archive", message)
    self.assertIn("empty", message)

  def test_parse_wprgo_archive(self):
    path = pth.LocalPath("/foo/bar/wprgo.archive")
    self.fs.create_file(path, st_size=1024)
    config = NetworkConfig.parse(str(path))
    assert isinstance(config, NetworkConfig)
    self.assertEqual(config.type, NetworkType.WPR)
    self.assertEqual(config.path, path)
    self.assertEqual(config.speed, NetworkSpeedConfig.default())

  def test_parse_wprgo_archive_url(self):
    url = "gs://bucket/wprgo.archive"
    config = NetworkConfig.parse(url)
    assert isinstance(config, NetworkConfig)
    self.assertEqual(config.type, NetworkType.WPR)
    self.assertEqual(config.url, url)
    self.assertEqual(config.speed, NetworkSpeedConfig.default())

  def test_invalid_constructor_params(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = NetworkConfig(path=pth.LocalPath("foo/bar"))
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = NetworkConfig(type=NetworkType.LOCAL, path=None)
    with self.assertRaises(argparse.ArgumentTypeError):
      _ = NetworkConfig(type=NetworkType.WPR, path=None)

  def test_parse_speed_preset(self):
    for preset in NetworkSpeedPreset:  # pytype: disable=missing-parameter
      config = NetworkConfig.parse_str(preset.value)
      self.assertEqual(config.speed, NetworkSpeedConfig.parse_preset(preset))

  def test_parse_live_preset(self):
    live_a = NetworkConfig.parse_live("4G")
    live_b = NetworkConfig.parse_live(NetworkSpeedConfig.parse("4G"))
    live_c = NetworkConfig.parse_live(
        NetworkSpeedConfig.parse(NetworkSpeedPreset.MOBILE_4G))
    live_d = NetworkConfig.parse_live(NetworkSpeedPreset.MOBILE_4G)
    self.assertEqual(live_a, live_b)
    self.assertEqual(live_a, live_c)
    self.assertEqual(live_a, live_d)

  def test_parse_wpr_invalid(self):
    dir_path = pth.LocalPath("test/dir")
    dir_path.mkdir(parents=True)
    for invalid in ("", "default", "4G", dir_path, str(dir_path)):
      with self.assertRaises(argparse.ArgumentTypeError):
        NetworkConfig.parse_wpr(invalid)

  def test_parse_wpr(self):
    archive_path = pth.LocalPath("test/archive.wprgo")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkConfig.parse_wpr(archive_path)
    self.assertIn(str(archive_path), str(cm.exception))
    self.fs.create_file(archive_path, st_size=100)
    config = NetworkConfig.parse_wpr(archive_path)
    self.assertEqual(config.type, NetworkType.WPR)
    self.assertEqual(config.speed, NetworkSpeedConfig.default())
    self.assertEqual(config.path, archive_path)
    self.assertEqual(config, NetworkConfig.parse(archive_path))

  def test_parse_dict_default(self):
    config = NetworkConfig.parse({})
    self.assertEqual(config, NetworkConfig.default())

  def test_parse_local_dict_default(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      # Missing path
      NetworkConfig.parse_local({})

  def test_parse_dict_speed(self):
    config_dict = {"speed": "4G"}
    config: NetworkConfig = NetworkConfig.parse(dict(config_dict))
    self.assertNotEqual(config, NetworkConfig.default())
    self.assertEqual(config.type, NetworkType.LIVE)
    self.assertEqual(
        config.speed,
        NetworkSpeedConfig.parse_preset(NetworkSpeedPreset.MOBILE_4G))
    self.assertIsNone(config.path)
    self.assertTrue(config_dict)
    config_1 = NetworkConfig.parse(json.dumps(config_dict))
    self.assertEqual(config, config_1)

  def test_parse_dict_wpr(self):
    archive_path = pth.LocalPath("test/archive.wprgo")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkConfig.parse({"type": "wpr", "path": archive_path})
    self.assertIn(str(archive_path), str(cm.exception))
    self.fs.create_file(archive_path, st_size=100)
    config_dict = {"type": "wpr", "path": str(archive_path)}
    config = NetworkConfig.parse(dict(config_dict))
    self.assertEqual(config, NetworkConfig.parse_wpr(archive_path))
    self.assertTrue(config_dict)
    config_1 = NetworkConfig.parse(json.dumps(config_dict))
    self.assertEqual(config, config_1)

  def test_parse_dict_local(self):
    benchmark_folder = pth.LocalPath("third_party/speedometer/v3.0")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkConfig.parse({"type": "local", "path": benchmark_folder})
    self.assertIn(str(benchmark_folder), str(cm.exception))
    self.fs.create_file(benchmark_folder / "index.html", st_size=100)
    url = "http://foo:1234"
    config_dict = {"type": "local", "path": str(benchmark_folder), "url": url}
    config = NetworkConfig.parse(dict(config_dict))
    self.assertEqual(config.type, NetworkType.LOCAL)
    self.assertEqual(config.path, benchmark_folder)
    self.assertEqual(config.url, url)
    self.assertTrue(config_dict)
    config_1 = NetworkConfig.parse(json.dumps(config_dict))
    self.assertEqual(config, config_1)
    local_config_dict = dict(config_dict)
    del local_config_dict["type"]
    config_local = NetworkConfig.parse_local(dict(local_config_dict))
    self.assertEqual(config, config_local)
    config_local = NetworkConfig.parse_local(json.dumps(local_config_dict))
    self.assertEqual(config, config_local)

  def test_parse_local_file(self):
    benchmark_folder = pth.LocalPath("third_party/speedometer/v3.0")
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkConfig.parse(benchmark_folder)
    self.assertIn(str(benchmark_folder), str(cm.exception))
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      NetworkConfig.parse_local(benchmark_folder)
    self.assertIn(str(benchmark_folder), str(cm.exception))
    self.fs.create_file(benchmark_folder / "index.html", st_size=100)
    config = NetworkConfig.parse(str(benchmark_folder))
    self.assertEqual(config.type, NetworkType.LOCAL)
    self.assertEqual(config.path, benchmark_folder)
    self.assertIsNone(config.url)
    self.assertEqual(config, NetworkConfig.parse(benchmark_folder))
    self.assertEqual(config, NetworkConfig.parse_local(str(benchmark_folder)))
    self.assertEqual(config, NetworkConfig.parse_local(benchmark_folder))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
