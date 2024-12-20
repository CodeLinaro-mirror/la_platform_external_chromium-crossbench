# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import unittest
from typing import cast

from crossbench.browsers.chrome.version import ChromeVersion
from crossbench.browsers.chromium.version import (ChromeDriverVersion,
                                                  ChromiumVersion)
from crossbench.browsers.firefox.version import FirefoxVersion
from crossbench.browsers.safari.version import SafariVersion
from crossbench.browsers.version import (BrowserVersion, BrowserVersionChannel,
                                         BrowserVersionParseError,
                                         PartialBrowserVersionError,
                                         UnknownBrowserVersion)
from tests import test_helper


class BrowserVersionChannelTestCase(unittest.TestCase):

  def test_unique(self):
    channels = set()
    names = set()
    indices = set()
    for channel in BrowserVersionChannel:
      self.assertNotIn(channel, channels)
      self.assertNotIn(channel.name, names)
      self.assertNotIn(channel.index, indices)
      channels.add(channel)
      names.add(channel.name)
      indices.add(channel.index)

  def test_name(self):
    self.assertEqual(BrowserVersionChannel.STABLE.label, "stable")
    self.assertEqual(str(BrowserVersionChannel.STABLE), "stable")

  def test_compare(self):
    self.assertLess(BrowserVersionChannel.LTS, BrowserVersionChannel.STABLE)
    self.assertLess(BrowserVersionChannel.STABLE, BrowserVersionChannel.BETA)
    self.assertLess(BrowserVersionChannel.BETA, BrowserVersionChannel.ALPHA)
    self.assertLess(BrowserVersionChannel.ALPHA,
                    BrowserVersionChannel.PRE_ALPHA)
    self.assertLessEqual(BrowserVersionChannel.PRE_ALPHA,
                         BrowserVersionChannel.PRE_ALPHA)

  def test_equal(self):
    self.assertEqual(BrowserVersionChannel.PRE_ALPHA,
                     BrowserVersionChannel.PRE_ALPHA)

  def test_sorting(self):
    unsorted = [
        BrowserVersionChannel.ALPHA, BrowserVersionChannel.PRE_ALPHA,
        BrowserVersionChannel.STABLE, BrowserVersionChannel.BETA,
        BrowserVersionChannel.LTS, BrowserVersionChannel.ANY
    ]
    self.assertListEqual(
        sorted(unsorted), [
            BrowserVersionChannel.LTS, BrowserVersionChannel.STABLE,
            BrowserVersionChannel.BETA, BrowserVersionChannel.ALPHA,
            BrowserVersionChannel.PRE_ALPHA, BrowserVersionChannel.ANY
        ])

  def test_compare_invalid(self):
    with self.assertRaises(TypeError):
      _ = BrowserVersionChannel.LTS < "some value"

  def test_matches_any(self):
    base = BrowserVersionChannel.ANY
    self.assertTrue(base.matches(BrowserVersionChannel.ANY))
    self.assertTrue(base.matches(BrowserVersionChannel.LTS))
    self.assertTrue(base.matches(BrowserVersionChannel.STABLE))
    self.assertTrue(base.matches(BrowserVersionChannel.BETA))
    self.assertTrue(base.matches(BrowserVersionChannel.ALPHA))
    self.assertTrue(base.matches(BrowserVersionChannel.PRE_ALPHA))

  def test_matches_other(self):
    test_channels = (BrowserVersionChannel.LTS, BrowserVersionChannel.STABLE,
                     BrowserVersionChannel.BETA, BrowserVersionChannel.ALPHA,
                     BrowserVersionChannel.PRE_ALPHA)
    for channel in test_channels:
      self.assertTrue(channel.matches(BrowserVersionChannel.ANY))
      self.assertTrue(channel.matches(channel))
      for other in test_channels:
        if other != channel:
          self.assertFalse(channel.matches(other))

  def test_matches_lts(self):
    base = BrowserVersionChannel.LTS
    self.assertTrue(base.matches(BrowserVersionChannel.ANY))
    self.assertTrue(base.matches(BrowserVersionChannel.LTS))
    self.assertFalse(base.matches(BrowserVersionChannel.STABLE))
    self.assertFalse(base.matches(BrowserVersionChannel.BETA))
    self.assertFalse(base.matches(BrowserVersionChannel.ALPHA))
    self.assertFalse(base.matches(BrowserVersionChannel.PRE_ALPHA))


class _BrowserVersionTestCase(unittest.TestCase, metaclass=abc.ABCMeta):
  ANY_VERSION_STR: str = ""
  LTS_VERSION_STR: str = ""
  STABLE_VERSION_STR: str = ""
  BETA_VERSION_STR: str = ""
  ALPHA_VERSION_STR: str = ""
  PRE_ALPHA_VERSION_STR: str = ""
  VERSION_CLS = BrowserVersion

  @abc.abstractmethod
  def parse(self, value: str) -> BrowserVersion:
    pass

  def _parse_helper(self, value: str):
    self.assertTrue(value)
    version: BrowserVersion = self.parse(value)
    self.assertGreater(version.major, 0)
    self.assertGreaterEqual(version.minor, 0)
    return version

  def test_parse_any(self):
    if self.ANY_VERSION_STR == "":
      self.skipTest(
          f"{type(self).__name__}: 'any'-channel version not supported")
    version: BrowserVersion = self._parse_helper(self.ANY_VERSION_STR)
    self.assertTrue(str(version))
    self.assertFalse(version.has_channel)
    with self.assertRaises(ValueError):
      _ = version.channel
    self.assertFalse(version.is_complete)
    self.assertTrue(version.has_complete_parts)
    self.assertFalse(version.is_lts)
    self.assertFalse(version.is_stable)
    self.assertFalse(version.is_beta)
    self.assertFalse(version.is_alpha)
    self.assertFalse(version.is_pre_alpha)
    self.assertEqual(version.channel_name, "any")
    self.assertTrue(version.key)
    _ = hash(version.key)
    self.assertEqual(version, self.VERSION_CLS.any(version.parts))

  def test_parse_lts(self):
    if self.LTS_VERSION_STR == "":
      self.skipTest(f"{type(self).__name__}: lts version not supported")
    version: BrowserVersion = self._parse_helper(self.LTS_VERSION_STR)
    self.assertEqual(version.channel, BrowserVersionChannel.LTS)
    self.assertTrue(version.is_complete)
    self.assertTrue(version.has_complete_parts)
    self.assertTrue(version.is_lts)
    self.assertFalse(version.is_stable)
    self.assertFalse(version.is_beta)
    self.assertFalse(version.is_alpha)
    self.assertFalse(version.is_pre_alpha)
    self.assertTrue(version.has_channel)
    self.assertTrue(version.channel_name)
    self.assertTrue(version.key)
    _ = hash(version.key)
    self.assertEqual(version, self.VERSION_CLS.lts(version.parts))


  def test_parse_stable(self):
    version: BrowserVersion = self._parse_helper(self.STABLE_VERSION_STR)
    self.assertEqual(version.channel, BrowserVersionChannel.STABLE)
    self.assertTrue(str(version))
    self.assertTrue(version.is_complete)
    self.assertTrue(version.has_complete_parts)
    self.assertFalse(version.is_lts)
    self.assertTrue(version.is_stable)
    self.assertFalse(version.is_beta)
    self.assertFalse(version.is_alpha)
    self.assertFalse(version.is_pre_alpha)
    self.assertTrue(version.has_channel)
    self.assertTrue(version.channel_name)
    self.assertTrue(version.key)
    _ = hash(version.key)
    self.assertEqual(version, self.VERSION_CLS.stable(version.parts))

  def test_parse_beta(self):
    if not self.BETA_VERSION_STR:
      self.skipTest(f"{type(self).__name__}: beta version not supported.")
    version: BrowserVersion = self._parse_helper(self.BETA_VERSION_STR)
    self.assertEqual(version.channel, BrowserVersionChannel.BETA)
    self.assertTrue(str(version))
    self.assertTrue(version.is_complete)
    self.assertTrue(version.has_complete_parts)
    self.assertFalse(version.is_lts)
    self.assertFalse(version.is_stable)
    self.assertTrue(version.is_beta)
    self.assertFalse(version.is_alpha)
    self.assertFalse(version.is_pre_alpha)
    self.assertTrue(version.has_channel)
    self.assertTrue(version.channel_name)
    self.assertTrue(version.key)
    _ = hash(version.key)
    self.assertEqual(version, self.VERSION_CLS.beta(version.parts))

  def test_parse_alpha(self):
    if self.ALPHA_VERSION_STR == "":
      self.skipTest(f"{type(self).__name__}: alpha version not supported")
    version: BrowserVersion = self._parse_helper(self.ALPHA_VERSION_STR)
    self.assertEqual(version.channel, BrowserVersionChannel.ALPHA)
    self.assertTrue(str(version))
    self.assertTrue(version.is_complete)
    self.assertTrue(version.has_complete_parts)
    self.assertFalse(version.is_lts)
    self.assertFalse(version.is_stable)
    self.assertFalse(version.is_beta)
    self.assertTrue(version.is_alpha)
    self.assertFalse(version.is_pre_alpha)
    self.assertTrue(version.has_channel)
    self.assertTrue(version.channel_name)
    self.assertTrue(version.key)
    _ = hash(version.key)
    self.assertEqual(version, self.VERSION_CLS.alpha(version.parts))

  def test_parse_pre_alpha(self):
    if self.PRE_ALPHA_VERSION_STR == "":
      self.skipTest(f"{type(self).__name__}: nightly version not supported")
    version: BrowserVersion = self._parse_helper(self.PRE_ALPHA_VERSION_STR)
    self.assertEqual(version.channel, BrowserVersionChannel.PRE_ALPHA)
    self.assertTrue(str(version))
    self.assertTrue(version.is_complete)
    self.assertTrue(version.has_complete_parts)
    self.assertFalse(version.is_lts)
    self.assertFalse(version.is_stable)
    self.assertFalse(version.is_beta)
    self.assertFalse(version.is_alpha)
    self.assertTrue(version.is_pre_alpha)
    self.assertTrue(version.has_channel)
    self.assertTrue(version.channel_name)
    self.assertTrue(version.key)
    _ = hash(version.key)
    self.assertEqual(version, self.VERSION_CLS.pre_alpha(version.parts))

  def test_equal_stable(self):
    version_a = self.parse(self.STABLE_VERSION_STR)
    version_b = self.parse(self.STABLE_VERSION_STR)
    self.assertEqual(version_a, version_a)
    self.assertEqual(version_a, version_b)
    self.assertEqual(version_b, version_a)

  def test_no_equal_stable_beta(self):
    if not self.BETA_VERSION_STR:
      self.skipTest(f"{type(self).__name__} :beta version not supported.")
    version_stable = self.parse(self.STABLE_VERSION_STR)
    version_beta = self.parse(self.BETA_VERSION_STR)
    self.assertNotEqual(version_stable, version_beta)
    self.assertNotEqual(version_beta, version_stable)

  def test_stable_lt_beta(self):
    if not self.BETA_VERSION_STR:
      self.skipTest(f"{type(self).__name__}: beta version not supported.")
    version_stable = self.parse(self.STABLE_VERSION_STR)
    version_beta = self.parse(self.BETA_VERSION_STR)
    # pylint: disable=comparison-with-itself
    self.assertFalse(version_stable > version_stable)
    self.assertFalse(version_stable < version_stable)
    self.assertTrue(version_stable >= version_stable)
    self.assertTrue(version_stable <= version_stable)
    self.assertLess(version_stable, version_beta)
    self.assertGreater(version_beta, version_stable)

  def test_invalid(self):
    with self.assertRaises(BrowserVersionParseError):
      self.parse("")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("no numbers here")

  def test_contains_basic(self):
    if not self.BETA_VERSION_STR:
      self.skipTest(f"{type(self).__name__}: beta version not supported.")
    version_stable = self.parse(self.STABLE_VERSION_STR)
    version_beta = self.parse(self.BETA_VERSION_STR)
    self.assertFalse(version_beta.contains(version_stable))
    self.assertFalse(version_stable.contains(version_beta))
    self.assertTrue(version_beta.contains(version_beta))
    self.assertTrue(version_stable.contains(version_stable))


class ChromiumVersionTestCase(_BrowserVersionTestCase):
  ANY_VERSION_STR = ""
  LTS_VERSION_STR = ""
  STABLE_VERSION_STR = "Google Chromium 115.0.5790.114"
  BETA_VERSION_STR = ""
  ALPHA_VERSION_STR = ""
  PRE_ALPHA_VERSION_STR = ""
  VERSION_CLS = ChromiumVersion

  def parse(self, value: str) -> ChromiumVersion:
    return ChromiumVersion.parse(value)

  def test_parse_invalid(self):
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chromium 115.0.5790.114.0.0.")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chromium 115.0.5790..114")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chromium 115.a.5790.114")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chromium 115 115.1.5790.114")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chromium ")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chromium")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chrome 115.1.5790.114")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chrome 115")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chrome M115")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chr M115")

  def test_init_invalid(self):
    with self.assertRaises(BrowserVersionParseError):
      ChromiumVersion(None)
    with self.assertRaises(BrowserVersionParseError):
      ChromiumVersion((-1, -2))

  def test_equal(self):
    self.assertEqual(self.parse("Chromium 125"), self.parse("125 Stable"))
    self.assertNotEqual(self.parse("Chromium 125"), self.parse("120 Stable"))
    self.assertEqual(self.parse("Chromium 120 Dev"), self.parse("120 Dev"))

  def test_parse_full(self):
    version = self.parse("Chromium 125.1.6416.3")
    self.assertTrue(version.is_stable)
    self.assertTrue(version.is_complete)
    self.assertTrue(version.has_complete_parts)
    self.assertEqual(str(version), "125.1.6416.3 stable")
    self.assertEqual(version.major, 125)
    self.assertEqual(version.minor, 1)
    self.assertEqual(version.build, 6416)
    self.assertEqual(version.patch, 3)
    self.assertEqual(version.parts_str, "125.1.6416.3")

  def parse_full_variants(self):
    self.assertEqual(
        self.parse("Chromium 125.1.6416.3"), self.parse("125.1.6416.3"))
    self.assertEqual(
        self.parse("Chromium 125.1.6416.3"), self.parse("M125.1.6416.3"))
    self.assertEqual(
        self.parse("Chromium 125.1.6416.3"), self.parse("m125.1.6416.3"))
    self.assertEqual(
        self.parse("Chromium 125.1.6416.3"), self.parse("125.1.6416.3 Stable"))
    self.assertEqual(
        self.parse("Chromium 125.1.6416.3"), self.parse("125.1.6416.3 stable"))

  def test_parse_milestone_variants(self):
    self.assertEqual(self.parse("Chromium 125"), self.parse("Chromium M125"))
    self.assertEqual(self.parse("Chromium 125"), self.parse("M125"))
    self.assertEqual(self.parse("Chromium 125"), self.parse("m125"))
    self.assertEqual(self.parse("Chromium 125"), self.parse("125"))
    self.assertEqual(self.parse("Chromium 125"), self.parse("125 Stable"))
    self.assertEqual(self.parse("Chromium 125"), self.parse("125 stable"))

  def test_parse_partial_milestone(self):
    version = self.parse("Chromium 125")
    self.assertTrue(version.is_stable)
    self.assertFalse(version.is_complete)
    self.assertFalse(version.has_complete_parts)
    self.assertEqual(str(version), "M125 stable")
    self.assertEqual(version.major, 125)
    self.assertEqual(version.parts_str, "125")
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.minor
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.build
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.patch

  def test_parse_partial_minor(self):
    version = self.parse("Chromium 125.3.X.X")
    self.assertTrue(version.is_stable)
    self.assertFalse(version.is_complete)
    self.assertFalse(version.has_complete_parts)
    self.assertEqual(str(version), "125.3.X.X stable")
    self.assertEqual(version.major, 125)
    self.assertEqual(version.minor, 3)
    self.assertEqual(version.parts_str, "125.3")
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.build
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.patch

  def test_parse_partial_build(self):
    version = self.parse("Chromium 125.3.1234.X")
    self.assertTrue(version.is_stable)
    self.assertFalse(version.is_complete)
    self.assertFalse(version.has_complete_parts)
    self.assertEqual(str(version), "125.3.1234.X stable")
    self.assertEqual(version.major, 125)
    self.assertEqual(version.minor, 3)
    self.assertEqual(version.build, 1234)
    self.assertEqual(version.parts_str, "125.3.1234")
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.patch


class ChromeBrowserVersionTestCase(_BrowserVersionTestCase):
  ANY_VERSION_STR = "Google Chrome 115.0.5790.114 Any"
  LTS_VERSION_STR = ""
  STABLE_VERSION_STR = "Google Chrome 115.0.5790.114"
  BETA_VERSION_STR = "Google Chrome 116.0.5845.50 beta"
  ALPHA_VERSION_STR = "Google Chrome 117.0.5911.2 dev"
  PRE_ALPHA_VERSION_STR = "Google Chrome 117.0.5921.0 canary"
  VERSION_CLS = ChromeVersion

  def parse(self, value: str) -> ChromeVersion:
    return ChromeVersion.parse(value)

  def test_parse_invalid(self):
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Google Chrome 115.0.5790.114.0.0.")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Google Chrome 115.0.5790..114")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Google Chrome 115.a.5790.114")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chrome ")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chrome 121 121")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chromium 115.1.5790.114")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chromium 115")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chromium X.X.X.X")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chromium M115")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("M1")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("1")
    with self.assertRaises(BrowserVersionParseError):
      ChromeVersion.parse_unique("1")
    _ = self.parse("123")
    with self.assertRaises(BrowserVersionParseError):
      ChromeVersion.parse_unique("123")

  def test_parse_variants(self):
    self.assertEqual(
        self.parse("Google Chrome 115.0.5790.114"),
        self.parse("Chrome 115.0.5790.114"))
    self.assertEqual(
        self.parse("Google Chrome 115.0.5790.114"),
        self.parse("M115.0.5790.114"))
    self.assertEqual(
        self.parse("Google Chrome 115.0.5790.114"),
        self.parse("chr 115.0.5790.114"))
    self.assertEqual(
        self.parse("Google Chrome 115.0.5790.114"),
        self.parse("chrome 115.0.5790.114"))
    self.assertEqual(
        self.parse("Google Chrome 115.0.5790.114"),
        self.parse("chr-115.0.5790.114"))
    self.assertEqual(
        self.parse("Google Chrome 115.0.5790.114"),
        self.parse("chrome-115.0.5790.114"))
    self.assertEqual(
        self.parse("Google Chrome 115.0.5790.114"),
        self.parse("chr m115.0.5790.114"))
    self.assertEqual(
        self.parse("Google Chrome 115.0.5790.114"),
        self.parse("chrome m115.0.5790.114"))

  def test_parse_channel(self):
    self.assertEqual(
        self.parse(self.BETA_VERSION_STR),
        self.parse("Google Chrome Beta 116.0.5845.50"))
    self.assertEqual(
        self.parse(self.ALPHA_VERSION_STR),
        self.parse("Google Chrome DEv 117.0.5911.2"))
    self.assertEqual(
        self.parse(self.PRE_ALPHA_VERSION_STR),
        self.parse("Google Chrome Canary 117.0.5921.0"))

  def test_str(self):
    self.assertEqual(
        str(self.parse(self.STABLE_VERSION_STR)), "115.0.5790.114 stable")
    self.assertEqual(
        str(self.parse(self.BETA_VERSION_STR)), "116.0.5845.50 beta")
    self.assertEqual(
        str(self.parse(self.ALPHA_VERSION_STR)), "117.0.5911.2 dev")
    self.assertEqual(
        str(self.parse(self.PRE_ALPHA_VERSION_STR)), "117.0.5921.0 canary")

  def test_parse_stable_chrome(self):
    version: BrowserVersion = self._parse_helper(self.STABLE_VERSION_STR)
    self.assertEqual(version.major, 115)
    self.assertEqual(version.minor, 0)
    self.assertEqual(version.minor, 0)
    self.assertEqual(version.channel_name, "stable")
    chrome_version = cast(ChromiumVersion, version)
    self.assertEqual(chrome_version.build, 5790)
    self.assertEqual(chrome_version.patch, 114)
    self.assertFalse(chrome_version.is_dev)
    self.assertFalse(chrome_version.is_canary)
    stable_version = ChromeVersion.stable(version.parts)
    self.assertEqual(stable_version, version)

  def test_parse_beta_chrome(self):
    version: BrowserVersion = self._parse_helper(self.BETA_VERSION_STR)
    self.assertEqual(version.major, 116)
    self.assertEqual(version.minor, 0)
    self.assertEqual(version.channel_name, "beta")
    chrome_version = cast(ChromiumVersion, version)
    self.assertEqual(chrome_version.build, 5845)
    self.assertEqual(chrome_version.patch, 50)
    self.assertFalse(chrome_version.is_dev)
    self.assertFalse(chrome_version.is_canary)
    beta_version = ChromeVersion.beta(version.parts)
    self.assertEqual(beta_version, version)

  def test_parse_alpha_chrome(self):
    version: BrowserVersion = self._parse_helper(self.ALPHA_VERSION_STR)
    self.assertEqual(version.major, 117)
    self.assertEqual(version.minor, 0)
    self.assertEqual(version.channel_name, "dev")
    chrome_version = cast(ChromiumVersion, version)
    self.assertEqual(chrome_version.build, 5911)
    self.assertEqual(chrome_version.patch, 2)
    self.assertTrue(chrome_version.is_dev)
    self.assertFalse(chrome_version.is_canary)
    alpha_version = ChromeVersion.alpha(version.parts)
    self.assertEqual(alpha_version, version)

  def test_parse_pre_alpha_chrome(self):
    version: BrowserVersion = self._parse_helper(self.PRE_ALPHA_VERSION_STR)
    self.assertEqual(version.major, 117)
    self.assertEqual(version.minor, 0)
    self.assertEqual(version.channel_name, "canary")
    chrome_version = cast(ChromiumVersion, version)
    self.assertEqual(chrome_version.build, 5921)
    self.assertEqual(chrome_version.patch, 0)
    self.assertFalse(chrome_version.is_dev)
    self.assertTrue(chrome_version.is_canary)
    pre_alpha_version = ChromeVersion.pre_alpha(version.parts)
    self.assertEqual(pre_alpha_version, version)

  def test_parse_partial_milestone(self):
    version = self.parse("Chrome 125")
    self.assertTrue(version.is_stable)
    self.assertTrue(version.has_channel)
    self.assertFalse(version.is_complete)
    self.assertFalse(version.has_complete_parts)
    self.assertEqual(str(version), "M125 stable")
    self.assertEqual(version.major, 125)
    self.assertEqual(version.parts_str, "125")
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.minor
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.build
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.patch

  def test_parse_partial_minor(self):
    version = self.parse("Chrome 125.3.X.X")
    self.assertTrue(version.is_stable)
    self.assertTrue(version.has_channel)
    self.assertFalse(version.is_complete)
    self.assertFalse(version.has_complete_parts)
    self.assertEqual(str(version), "125.3.X.X stable")
    self.assertEqual(version.major, 125)
    self.assertEqual(version.minor, 3)
    self.assertEqual(version.parts_str, "125.3")
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.build
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.patch

  def test_parse_partial_build(self):
    version = self.parse("Chrome 125.3.1234.X")
    self.assertTrue(version.is_stable)
    self.assertTrue(version.has_channel)
    self.assertFalse(version.is_complete)
    self.assertFalse(version.has_complete_parts)
    self.assertEqual(str(version), "125.3.1234.X stable")
    self.assertEqual(version.major, 125)
    self.assertEqual(version.minor, 3)
    self.assertEqual(version.build, 1234)
    self.assertEqual(version.parts_str, "125.3.1234")
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.patch

  def test_parse_partial_channel(self):
    version = self.parse("Chrome Stable")
    self.assertTrue(version.is_stable)
    self.assertTrue(version.has_channel)
    self.assertFalse(version.is_complete)
    self.assertFalse(version.has_complete_parts)
    self.assertEqual(str(version), "stable")
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.major
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.minor
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.build
    with self.assertRaises(PartialBrowserVersionError):
      _ = version.patch

  def test_parse_partial_channels(self):
    version = self.parse("Chrome Extended")
    self.assertTrue(version.is_lts)
    version = self.parse("Chrome Stable")
    self.assertTrue(version.is_stable)
    version = self.parse("Chrome Beta")
    self.assertTrue(version.is_beta)
    version = self.parse("Chrome Dev")
    self.assertTrue(version.is_alpha)
    version = self.parse("Chrome Canary")
    self.assertTrue(version.is_pre_alpha)

  def test_compare_channel(self):
    canary_version = self.parse(self.PRE_ALPHA_VERSION_STR)
    dev_channel = self.parse("Chrome Dev")
    stable_channel = self.parse("Chrome Stable")
    dev_version = self.parse(self.ALPHA_VERSION_STR)
    with self.assertRaises(ValueError):
      _ = canary_version <= dev_channel
    with self.assertRaises(ValueError):
      _ = stable_channel <= dev_version
    self.assertLess(stable_channel, dev_channel)
    self.assertEqual(stable_channel, stable_channel)
    self.assertEqual(dev_channel, dev_channel)

  def test_compare_version_different_channels(self):
    any_125_version = self.parse("Chrome 125.3.1234.60 any")
    extended_125_version = self.parse("Chrome 125.3.1234.60 extended")
    beta_125_version = self.parse("Chrome 125.3.1234.60 beta")
    stable_125_version = self.parse("Chrome 125.3.1234.60 stable")
    beta_120_version = self.parse("Chrome 120.3.1234.60 beta")
    stable_120_version = self.parse("Chrome 120.3.1234.60 stable")
    self.assertFalse(any_125_version.has_channel)
    self.assertTrue(extended_125_version.is_lts)
    self.assertTrue(stable_125_version.is_stable)
    self.assertTrue(beta_125_version.is_beta)
    self.assertTrue(stable_120_version.is_stable)
    self.assertTrue(beta_120_version.is_beta)

    self.assertLess(extended_125_version, beta_125_version)
    self.assertLess(stable_125_version, beta_125_version)
    self.assertLess(beta_120_version, beta_125_version)

    self.assertLess(beta_120_version, extended_125_version)
    self.assertLess(beta_120_version, stable_125_version)

    self.assertLess(stable_120_version, beta_125_version)
    self.assertLess(stable_120_version, extended_125_version)
    self.assertLess(stable_120_version, stable_125_version)
    self.assertLess(stable_120_version, beta_120_version)

    self.assertNotEqual(stable_125_version, extended_125_version)
    self.assertNotEqual(stable_125_version, beta_125_version)
    self.assertNotEqual(stable_125_version, stable_120_version)
    self.assertNotEqual(extended_125_version, beta_125_version)
    self.assertNotEqual(extended_125_version, stable_120_version)

  def test_parse_full_version_macos(self):
    version = self.parse("125.0.6422.60 (Official Build) (arm64) ")
    self.assertTrue(version.is_stable)
    self.assertTrue(version.parts, (125, 0, 6422, 60))
    version = self.parse("127.0.6490.1 (Official Build) canary (arm64) ")
    self.assertTrue(version.is_pre_alpha)
    self.assertTrue(version.parts, (127, 0, 6490, 1))

  def test_parse_full_version_linux(self):
    version = self.parse("125.0.6422.60 (Official Build) (64-bit) ")
    self.assertTrue(version.is_stable)
    self.assertTrue(version.parts, (125, 0, 6422, 60))
    version = self.parse("126.0.6478.7 (Official Build) beta (64-bit) ")
    self.assertTrue(version.is_beta)
    self.assertTrue(version.parts, (126, 0, 6478, 7))

  def test_contains_channel(self):
    any_125_milestone = self.parse("Chrome M125 any")
    beta_125_version = self.parse("Chrome 125.3.1234.60 beta")
    stable_125_version = self.parse("Chrome 125.3.1234.60 stable")
    channel_stable = self.parse("Chrome Stable")
    channel_beta = self.parse("Chrome Beta")
    milestone_125_stable = self.parse("Chrome M125 Stable")
    milestone_125_beta = self.parse("Chrome M125 beta")

    self.assertFalse(any_125_milestone.has_channel)
    self.assertTrue(beta_125_version.has_channel)

    self.assertTrue(any_125_milestone.contains(stable_125_version))
    self.assertTrue(channel_stable.contains(stable_125_version))
    self.assertFalse(channel_beta.contains(stable_125_version))
    self.assertTrue(milestone_125_stable.contains(stable_125_version))
    self.assertFalse(milestone_125_beta.contains(stable_125_version))

    self.assertTrue(any_125_milestone.contains(beta_125_version))
    self.assertFalse(channel_stable.contains(beta_125_version))
    self.assertTrue(channel_beta.contains(beta_125_version))
    self.assertFalse(milestone_125_stable.contains(beta_125_version))
    self.assertTrue(milestone_125_beta.contains(beta_125_version))

    self.assertTrue(any_125_milestone.contains(milestone_125_stable))
    self.assertTrue(channel_stable.contains(milestone_125_stable))
    self.assertFalse(channel_beta.contains(milestone_125_stable))
    self.assertTrue(channel_stable.contains(milestone_125_stable))
    self.assertFalse(channel_beta.contains(milestone_125_stable))

    self.assertTrue(milestone_125_stable.contains(any_125_milestone))
    self.assertTrue(channel_stable.contains(any_125_milestone))
    self.assertTrue(channel_beta.contains(any_125_milestone))
    self.assertTrue(channel_stable.contains(any_125_milestone))
    self.assertTrue(channel_beta.contains(any_125_milestone))

    self.assertFalse(any_125_milestone.contains(channel_beta))
    self.assertFalse(beta_125_version.contains(channel_beta))
    self.assertFalse(stable_125_version.contains(channel_beta))
    self.assertFalse(channel_stable.contains(channel_beta))
    self.assertTrue(channel_beta.contains(channel_beta))
    self.assertFalse(milestone_125_stable.contains(channel_beta))
    self.assertFalse(milestone_125_beta.contains(channel_beta))


class ChromeDriverBrowserVersionTestCase(_BrowserVersionTestCase):
  ANY_VERSION_STR = ""
  LTS_VERSION_STR = ""
  STABLE_VERSION_STR = ("ChromeDriver 115.0.5790.114 "
                        "(386bc09e8f4f2e025eddae123f36f6263096ae49-"
                        "refs/branch-heads/5735@{#1052})")
  BETA_VERSION_STR = ""
  ALPHA_VERSION_STR = ""
  PRE_ALPHA_VERSION_STR = ("ChromeDriver 126.0.6424.0 "
                           "(0000000000000000000000000000000000000000-"
                           "0000000000000000000000000000000000000000)")
  VERSION_CLS = ChromeDriverVersion

  def parse(self, value: str) -> BrowserVersion:
    return ChromeDriverVersion.parse(value)


class FirefoxVersionTestCase(_BrowserVersionTestCase):
  ANY_VERSION_STR = "Mozilla Firefox 114.0.1 any"
  LTS_VERSION_STR = "Mozilla Firefox 114.0.1esr"
  STABLE_VERSION_STR = "Mozilla Firefox 115.0.3"
  # IRL Firefox version numbers do not distinct beta from stable. so we
  # remap Firefox Dev => beta.
  BETA_VERSION_STR = "Mozilla Firefox 116.0b4"
  ALPHA_VERSION_STR = "Mozilla Firefox 117.0a1"
  PRE_ALPHA_VERSION_STR = ""
  VERSION_CLS = FirefoxVersion

  def parse(self, value: str) -> BrowserVersion:
    return FirefoxVersion.parse(value)

  def test_parse_invalid(self):
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Mozilla Firefox 116.0b4esr")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Mozilla Firefox 116.0X4")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Mozilla Firefox 116.0a4b5")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Mozilla Firefox 116.10.0.1")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Mozilla Firefox 116.0a1.2")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Mozilla Firefox 116.10.0a")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Mozilla Firefox 116.10.1.0a")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Mozilla Firefox 116..0a")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("Chrome 116.0a1")

  def test_parse_lts_firefox(self):
    version: BrowserVersion = self._parse_helper(self.LTS_VERSION_STR)
    self.assertEqual(version.major, 114)
    self.assertEqual(version.minor, 0)
    self.assertEqual(version.channel_name, "esr")
    self.assertTrue(version.is_lts)
    version = self._parse_helper("115.8.0esr")
    self.assertEqual(version.major, 115)
    self.assertEqual(version.minor, 8)
    self.assertEqual(version.channel_name, "esr")
    self.assertTrue(version.is_lts)

  def test_parse_stable_firefox(self):
    version: BrowserVersion = self._parse_helper(self.STABLE_VERSION_STR)
    self.assertEqual(version.major, 115)
    self.assertEqual(version.minor, 0)
    self.assertEqual(version.channel_name, "stable")

  def test_parse_beta_firefox(self):
    version: BrowserVersion = self._parse_helper(self.BETA_VERSION_STR)
    self.assertEqual(version.major, 116)
    self.assertEqual(version.minor, 0)
    self.assertEqual(version.channel_name, "dev")

  def test_parse_alpha_firefox(self):
    version: BrowserVersion = self._parse_helper(self.ALPHA_VERSION_STR)
    self.assertEqual(version.major, 117)
    self.assertEqual(version.minor, 0)
    self.assertEqual(version.channel_name, "nightly")

  def test_str(self):
    self.assertEqual(str(self.parse(self.LTS_VERSION_STR)), "114.0.1 esr")
    self.assertEqual(str(self.parse(self.STABLE_VERSION_STR)), "115.0.3 stable")
    self.assertEqual(str(self.parse(self.BETA_VERSION_STR)), "116.0b4 dev")
    self.assertEqual(str(self.parse(self.ALPHA_VERSION_STR)), "117.0a1 nightly")


class SafariBrowserVersionTestCase(_BrowserVersionTestCase):
  ANY_VERSION_STR = "16.6 Included with Safari 16.6 (18615.3.12.11.2) Any"
  LTS_VERSION_STR = ""
  # Additionally use the `safaridriver --version``
  STABLE_VERSION_STR = "16.6 Included with Safari 16.6 (18615.3.12.11.2)"
  BETA_VERSION_STR = ("17.0 Included with Safari Technology Preview "
                      "(Release 175, 18617.1.1.2)")
  ALPHA_VERSION_STR = ""
  PRE_ALPHA_VERSION_STR = ""
  VERSION_CLS = SafariVersion

  def parse(self, value: str) -> BrowserVersion:
    return SafariVersion.parse(value)

  def test_parse_invalid(self):
    with self.assertRaises(BrowserVersionParseError):
      self.parse("(Release 175, 18617.1.1.2)")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("16.7 (Release 175, 18617.1.1.2)")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("16.7 XXX (Release, 18617.1.1.2)")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("16.6 XXX (18615.3...12.11.2)")
    with self.assertRaises(BrowserVersionParseError):
      self.parse("16.6 XXX (18615.3)")

  def test_parse_stable_safari(self):
    version: BrowserVersion = self._parse_helper(self.STABLE_VERSION_STR)
    self.assertEqual(version.major, 16)
    self.assertEqual(version.minor, 6)
    safari_version = cast(SafariVersion, version)
    self.assertFalse(safari_version.is_tech_preview)
    self.assertEqual(safari_version.release, 0)
    self.assertEqual(version.channel_name, "stable")

  def test_parse_beta_safari(self):
    version: BrowserVersion = self._parse_helper(self.BETA_VERSION_STR)
    self.assertEqual(version.major, 17)
    self.assertEqual(version.minor, 0)
    safari_version = cast(SafariVersion, version)
    self.assertTrue(safari_version.is_tech_preview)
    self.assertEqual(safari_version.release, 175)
    self.assertEqual(version.channel_name, "technology preview")

  def test_str(self):
    self.assertEqual(
        str(self.parse(self.STABLE_VERSION_STR)),
        "16.6 (18615.3.12.11.2) stable")
    self.assertEqual(
        str(self.parse(self.BETA_VERSION_STR)),
        "17.0 (Release 175, 18617.1.1.2) technology preview")


class BrowserVersionTestCase(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    self.sf_version = SafariVersion.parse(
        "16.6 Included with Safari 16.6 (18615.3.12.11.2)")
    self.chr_version = ChromeVersion.parse("Google Chrome 117.0.5911.2 dev")

  def test_cross_browser_compare(self):
    self.assertFalse(self.sf_version == self.chr_version)
    with self.assertRaises(TypeError):
      _ = self.sf_version <= self.chr_version
    with self.assertRaises(TypeError):
      _ = self.chr_version <= self.sf_version

  def check_not_valid_unique(self, value: str):
    self.assertFalse(ChromeVersion.is_valid_unique(value))
    self.assertFalse(FirefoxVersion.is_valid_unique(value))
    self.assertFalse(SafariVersion.is_valid_unique(value))

  def test_not_valid_unique(self):
    self.check_not_valid_unique("123")
    self.check_not_valid_unique("123.1")
    self.check_not_valid_unique("123.1.3")
    self.check_not_valid_unique("123.1.3.2")

  def check_is_valid_unique(self, value: str):
    valid = (ChromeVersion.is_valid_unique(value),
             FirefoxVersion.is_valid_unique(value),
             SafariVersion.is_valid_unique(value))
    self.assertEqual(sum(valid), 1)

  def test_is_valid_unique(self):
    for prefix in ("chr", "chr-", "chr", "chrome", "chrome-"):
      with self.subTest(prefix=prefix):
        self.check_is_valid_unique(f"{prefix}123")
        self.check_is_valid_unique(f"{prefix}123.1.3.2")
      self.check_is_valid_unique("123.1b3")
      self.check_is_valid_unique("ff-123.1.3")
      self.check_is_valid_unique("firefox-123.1a3")
      self.check_is_valid_unique("ff-123.1b3")

  def test_contains_invalid(self):
    with self.assertRaises(TypeError):
      self.sf_version.contains(self.chr_version)
    with self.assertRaises(TypeError):
      self.chr_version.contains(self.sf_version)


class UnknownBrowserVersionTestCase(unittest.TestCase):

  def test_init(self):
    with self.assertRaises(RuntimeError):
      UnknownBrowserVersion.parse("")

  def test_attributes(self):
    version = UnknownBrowserVersion()
    self.assertFalse(version.has_channel)
    self.assertFalse(version.is_complete)
    self.assertFalse(version.has_complete_parts)
    self.assertFalse(version.is_stable)
    self.assertFalse(version.is_beta)
    self.assertFalse(version.is_alpha)
    self.assertFalse(version.is_pre_alpha)
    self.assertEqual(version.parts, ())

  def test_compare(self):
    version = UnknownBrowserVersion()
    chr_version = ChromeVersion.parse("Google Chrome 117.0.5911.2 dev")
    self.assertFalse(version == chr_version)
    with self.assertRaises(TypeError):
      _ = version <= chr_version
    with self.assertRaises(TypeError):
      _ = chr_version <= version


# Hide the abstract base test class from all test runner
del _BrowserVersionTestCase

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
