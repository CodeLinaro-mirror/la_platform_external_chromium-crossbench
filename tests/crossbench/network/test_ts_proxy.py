# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import pathlib
from unittest import mock

from crossbench.network.traffic_shaping.ts_proxy import (TsProxyProcess,
                                                         TsProxyServer,
                                                         TsProxyTrafficShaper)
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase


class TsProxyBaseTestCase(BaseCrossbenchTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.ts_proxy_path = pathlib.Path("/chrome/tsproxy/tsproxy.py")
    self.fs.create_file(self.ts_proxy_path, st_size=100)
    # Avoid dealing with fcntl for testing.
    patcher = mock.patch.object(
        TsProxyProcess, "_setup_non_blocking_io", return_value=None)
    self.addCleanup(patcher.stop)
    patcher.start()


class TsProxyTestCase(TsProxyBaseTestCase):

  def test_ts_proxy_traffic_shaper_no_tsproxy(self):
    with self.assertRaises(RuntimeError):
      TsProxyTrafficShaper(self.platform)

  def test_ts_proxy_traffic_shaper_default(self):
    ts_proxy = TsProxyTrafficShaper(self.platform, self.ts_proxy_path)
    self.assertFalse(ts_proxy.is_running)


class TsProxyServerTestCase(TsProxyBaseTestCase):

  def test_construct_invalid(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      TsProxyServer(pathlib.Path("does/not/exist"))

  def test_basic_instance(self):
    server = TsProxyServer(self.ts_proxy_path)
    self.assertFalse(server.is_running)

    with self.assertRaises(AssertionError):
      server.set_traffic_settings()
    with self.assertRaises(AssertionError):
      _ = server.socks_proxy_port
    self.assertIsNone(server.stop())

  def test_basic_instance_http_port(self):
    server = TsProxyServer(self.ts_proxy_path, http_port=8080)
    self.assertFalse(server.is_running)
    with self.assertRaises(AssertionError):
      _ = server.socks_proxy_port
    self.assertIsNone(server.stop())

  def test_ports(self):
    with self.assertRaises(ValueError):
      TsProxyServer(self.ts_proxy_path, https_port=400)
    with self.assertRaises(ValueError):
      TsProxyServer(self.ts_proxy_path, http_port=400, https_port=400)
    with self.assertRaises(argparse.ArgumentTypeError):
      TsProxyServer(self.ts_proxy_path, http_port=-400, https_port=400)
    with self.assertRaises(argparse.ArgumentTypeError):
      TsProxyServer(self.ts_proxy_path, http_port=400, https_port=-400)

  def test_start_server(self):
    server = TsProxyServer(self.ts_proxy_path)

    proc = mock.Mock()
    proc.configure_mock(**{
        "poll.return_value": None,
        "communicate.return_value": (None, None)
    })
    proc.stdout = mock.Mock()
    proc.stdout.configure_mock(**{
        "readline.return_value":
            "Started Socks5 proxy server on 127.0.0.1:43210"
    })
    proc.stderr = mock.Mock()

    def popen_mock(cmd, *args, **kwargs):
      self.assertEqual(cmd[1], self.ts_proxy_path)
      self.assertEqual(cmd[2], "--port=0")
      del args, kwargs
      return proc

    with mock.patch("subprocess.Popen", side_effect=popen_mock) as popen:
      self.assertFalse(server.is_running)
      with server:
        self.assertTrue(server.is_running)
        self.assertEqual(server.socks_proxy_port, 43210)
        proc.stdout.readline.assert_called_once()
        # Set return value for exit command.
        proc.stdout.readline.return_value = "OK"
      self.assertFalse(server.is_running)

    popen.assert_called_once()
    proc.stdin.write.assert_called_with("exit\n")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
