# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest

from crossbench import path as pth
from crossbench import plt
from crossbench.browsers.settings import Settings
from crossbench.browsers.splash_screen import SplashScreen
from crossbench.browsers.viewport import Viewport
from crossbench.flags.base import Flags
from crossbench.flags.chrome import ChromeFlags
from crossbench.flags.js_flags import JSFlags


class SettingsTestCase(unittest.TestCase):

  def test_defaults(self):
    settings = Settings()
    self.assertEqual(settings.flags, Flags())
    self.assertEqual(settings.js_flags, Flags())
    self.assertIsNone(settings.cache_dir)
    self.assertEqual(settings.viewport, Viewport.DEFAULT)
    self.assertIsNone(settings.driver_path)
    self.assertEqual(settings.splash_screen, SplashScreen.DEFAULT)
    self.assertTrue(settings.network.is_live)
    self.assertEqual(settings.platform, plt.PLATFORM)

  def test_custom(self):
    flags = Flags({"--one":"1", "--two":"2"}).freeze()
    js_flags = Flags({"--js-one":"js-1", "--js-two":"js-2"}).freeze()
    settings = Settings(flags, js_flags,
                        cache_dir=pth.LocalPath("cache"),
                        viewport=Viewport.FULLSCREEN,
                        driver_path=pth.LocalPath("driver"),
                        splash_screen=SplashScreen.DETAILED,
                        )
    self.assertEqual(settings.flags, flags)
    self.assertEqual(settings.js_flags, js_flags)
    self.assertEqual(settings.cache_dir, pth.LocalPath("cache"))
    self.assertEqual(settings.viewport, Viewport.FULLSCREEN)
    self.assertEqual(settings.driver_path, pth.LocalPath("driver"))
    self.assertEqual(settings.splash_screen, SplashScreen.DETAILED)
    self.assertTrue(settings.network.is_live)

  def test_js_flags_alone(self):
    js_flags = Flags({"--js-one":"js-1", "--js-two":"js-2"}).freeze()
    settings = Settings(js_flags=js_flags)
    self.assertEqual(settings.flags, Flags())
    self.assertEqual(settings.js_flags, js_flags)

  def test_chrome_flags(self):
    flags = ChromeFlags({"--one":"1", "--two":"2"}).freeze()
    settings = Settings(flags)
    self.assertEqual(settings.flags, flags)
    self.assertIsInstance(settings.flags, ChromeFlags)
    self.assertEqual(settings.js_flags, JSFlags())
    self.assertIsInstance(settings.js_flags, JSFlags)

  def test_chrome_flags_js_flags(self):
    flags = ChromeFlags({"--one":"1", "--two":"2", "--js-flags": "--js-one=js-1"}).freeze()
    settings = Settings(flags)
    self.assertEqual(settings.flags, flags)
    self.assertIsInstance(settings.flags, ChromeFlags)
    self.assertEqual(settings.js_flags, JSFlags({"--js-one":"js-1"}))
    self.assertIsInstance(settings.js_flags, JSFlags)

  def test_chrome_flags_separate_js_flags(self):
    flags = ChromeFlags({"--one":"1", "--two":"2"}).freeze()
    js_flags = Flags({"--js-one":"js-1", "--js-two":"js-2"}).freeze()
    settings = Settings(flags, js_flags)
    self.assertEqual(settings.flags, flags)
    self.assertIsInstance(settings.flags, ChromeFlags)
    self.assertEqual(settings.js_flags, js_flags)
    self.assertIsInstance(settings.js_flags, Flags)

  def test_ambiguous_js_flags(self):
    flags = ChromeFlags({"--one":"1", "--js-flags":"--js-one=js-1"}).freeze()
    with self.assertRaises(ValueError) as cm:
      _ = Settings(flags, js_flags=Flags({"--js-two": "js-2"}))
    self.assertIn("js-flags", str(cm.exception))
