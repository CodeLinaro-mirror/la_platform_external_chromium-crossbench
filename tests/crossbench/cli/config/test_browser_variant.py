# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import copy
import json
import unittest
from typing import Dict, Tuple, Type
from unittest import mock

import hjson

from crossbench import path as pth
from crossbench import plt
from crossbench.browsers.chrome.chrome import Chrome
from crossbench.browsers.chrome.webdriver import ChromeWebDriver
from crossbench.browsers.safari.safari import Safari
from crossbench.cli.config.browser import BrowserConfig
from crossbench.cli.config.browser_variants import BrowserVariantsConfig
from crossbench.cli.config.driver import BrowserDriverType
from crossbench.cli.config.network import NetworkConfig
from crossbench.config import ConfigError
from tests import test_helper
from tests.crossbench import mock_browser
from tests.crossbench.cli.config.base import (ADB_DEVICES_SINGLE_OUTPUT,
                                              BaseConfigTestCase)
from tests.crossbench.mock_helper import AndroidAdbMockPlatform, MockAdb


class TestBrowserVariantsConfig(BaseConfigTestCase):
  # pylint: disable=expression-not-assigned

  EXAMPLE_CONFIG_PATH = (test_helper.config_dir() / "doc/browser.config.hjson")

  EXAMPLE_REMOTE_CONFIG_PATH = (
      test_helper.config_dir() / "doc/remote_browser.config.hjson")

  def setUp(self):
    super().setUp()
    self.browser_lookup: Dict[str, Tuple[
        Type[mock_browser.MockBrowser], BrowserConfig]] = {
            "chr-stable":
                (mock_browser.MockChromeStable,
                 BrowserConfig(mock_browser.MockChromeStable.mock_app_path())),
            "chr-dev":
                (mock_browser.MockChromeDev,
                 BrowserConfig(mock_browser.MockChromeDev.mock_app_path())),
            "chrome-stable":
                (mock_browser.MockChromeStable,
                 BrowserConfig(mock_browser.MockChromeStable.mock_app_path())),
            "chrome-dev":
                (mock_browser.MockChromeDev,
                 BrowserConfig(mock_browser.MockChromeDev.mock_app_path())),
        }
    for _, (_, browser_config) in self.browser_lookup.items():
      self.assertTrue(browser_config.path.exists())

  def _expect_linux_ssh(self, cmd, **kwargs):
    return self.platform.expect_sh("ssh", "-p", "22", "user@my-linux-machine",
                                   cmd, **kwargs)

  def _expect_chromeos_ssh(self, cmd, **kwargs):
    return self.platform.expect_sh("ssh", "-p", "22",
                                   "root@my-chromeos-machine", cmd, **kwargs)

  def test_parse_browser_config_template(self):
    if not self.EXAMPLE_CONFIG_PATH.exists():
      raise unittest.SkipTest(
          f"Test file {self.EXAMPLE_CONFIG_PATH} does not exist")
    self.fs.add_real_file(self.EXAMPLE_CONFIG_PATH)
    with self.EXAMPLE_CONFIG_PATH.open(encoding="utf-8") as f:
      config = BrowserVariantsConfig(
          browser_lookup_override=self.browser_lookup)
      config.parse_text_io(f, args=self.mock_args)
    self.assertIn("flag-group-1", config.flags_config)
    self.assertGreaterEqual(len(config.flags_config), 1)
    self.assertGreaterEqual(len(config.variants), 1)

  def test_parse_remote_browser_config_template(self):
    if not self.EXAMPLE_REMOTE_CONFIG_PATH.exists():
      raise unittest.SkipTest(
          f"Test file {self.EXAMPLE_REMOTE_CONFIG_PATH} does not exist")
    self.fs.add_real_file(self.EXAMPLE_REMOTE_CONFIG_PATH)

    self._expect_linux_ssh("uname -m", result="arm64")
    self._expect_linux_ssh("'[' -e /path/to/google/chrome ']'")
    self._expect_linux_ssh("'[' -f /path/to/google/chrome ']'")
    self._expect_linux_ssh("'[' -e /path/to/google/chrome ']'")
    self._expect_linux_ssh(
        "/path/to/google/chrome --version", result='102.22.33.44')
    self._expect_linux_ssh("env")
    self._expect_linux_ssh("'[' -d /tmp ']'")
    self._expect_linux_ssh("mktemp -d /tmp/chrome.XXXXXXXXXXX")

    self._expect_chromeos_ssh("'[' -e /usr/local/autotest/bin/autologin.py ']'")
    self._expect_chromeos_ssh("uname -m", result="arm64")
    self._expect_chromeos_ssh("'[' -e /opt/google/chrome/chrome ']'")
    self._expect_chromeos_ssh("'[' -f /opt/google/chrome/chrome ']'")
    self._expect_chromeos_ssh("'[' -e /opt/google/chrome/chrome ']'")
    self._expect_chromeos_ssh(
        "/opt/google/chrome/chrome --version", result='125.0.6422.60')
    self._expect_chromeos_ssh("env")
    self._expect_chromeos_ssh("'[' -d /tmp ']'")
    self._expect_chromeos_ssh("mktemp -d /tmp/chrome.XXXXXXXXXXX")

    with self.EXAMPLE_REMOTE_CONFIG_PATH.open(encoding="utf-8") as f:
      config = BrowserVariantsConfig()
      config.parse_text_io(f, args=self.mock_args)
      self.assertEqual(len(config.variants), 2)
      for variant in config.variants:
        self.assertTrue(variant.platform.is_remote)
        self.assertTrue(variant.platform.is_linux)
      self.assertEqual(config.variants[0].platform.name, 'linux_ssh')
      self.assertEqual(config.variants[1].platform.name, 'chromeos_ssh')
      self.assertEqual(config.variants[0].version, '102.22.33.44')
      self.assertEqual(config.variants[1].version, '125.0.6422.60')

  def test_browser_labels_attributes(self):
    browsers = BrowserVariantsConfig(
        {
            "browsers": {
                "chrome-stable-default": {
                    "path": "chrome-stable",
                },
                "chrome-stable-noopt": {
                    "path": "chrome-stable",
                    "flags": ["--js-flags=--max-opt=0",]
                },
                "chrome-stable-custom": {
                    "label": "custom-label-property",
                    "path": "chrome-stable",
                    "flags": ["--js-flags=--max-opt=0",]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args).variants
    self.assertEqual(len(browsers), 3)
    self.assertEqual(browsers[0].label, "chrome-stable-default")
    self.assertEqual(browsers[1].label, "chrome-stable-noopt")
    self.assertEqual(browsers[2].label, "custom-label-property")

  def test_browser_label_args(self):
    self.platform.sh_results = [ADB_DEVICES_SINGLE_OUTPUT]
    args = self.mock_args
    adb_config = BrowserConfig.parse("adb:chrome")
    desktop_config = BrowserConfig.parse("chrome")
    args.browser = [
        adb_config,
        desktop_config,
    ]
    self.assertFalse(self.platform.sh_results)
    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT,
        ADB_DEVICES_SINGLE_OUTPUT,
    ]

    def mock_get_browser_cls(browser_config: BrowserConfig):
      if browser_config is adb_config:
        return mock_browser.MockChromeAndroidStable
      if browser_config is desktop_config:
        return mock_browser.MockChromeStable
      raise ValueError("Unknown browser_config")

    with mock.patch.object(
        BrowserVariantsConfig,
        "_get_browser_cls",
        side_effect=mock_get_browser_cls), mock.patch(
            "crossbench.plt.android_adb.AndroidAdbPlatform.machine",
            new_callable=mock.PropertyMock,
            return_value=plt.MachineArch.ARM_64):
      browsers = BrowserVariantsConfig.from_cli_args(args).variants
    self.assertEqual(len(browsers), 2)
    self.assertEqual(browsers[0].label, "android.arm64.remote_0")
    self.assertEqual(browsers[1].label, f"{self.platform}_1")

    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "browsers": {
                  "chrome-stable-label": {
                      "path": "chrome-stable",
                  },
                  "chrome-stable-custom": {
                      "label": "chrome-stable-label",
                      "path": "chrome-stable",
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    message = str(cm.exception)
    self.assertIn("chrome-stable-label", message)
    self.assertIn("chrome-stable-custom", message)

  def test_parse_invalid_browser_type(self):
    for invalid in (None, 1, []):
      with self.assertRaises(ConfigError) as cm:
        _ = BrowserVariantsConfig(
            {
                "browsers": {
                    "chrome-stable-default": invalid
                }
            },
            args=self.mock_args).variants
      self.assertIn("Expected str or dict", str(cm.exception))

  def test_browser_custom_driver_variants(self):
    self.platform.sh_results = [
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT,
        ADB_DEVICES_SINGLE_OUTPUT, ADB_DEVICES_SINGLE_OUTPUT
    ]

    def mock_get_browser_platform(
        browser_config: BrowserConfig) -> plt.Platform:
      if browser_config.driver.type == BrowserDriverType.ANDROID:
        return AndroidAdbMockPlatform(self.platform, adb=MockAdb(self.platform))
      return self.platform

    with self.mock_chrome_stable(
        mock_browser.MockChromeAndroidStable), mock.patch.object(
            BrowserVariantsConfig,
            "_get_browser_platform",
            side_effect=mock_get_browser_platform):
      browsers = BrowserVariantsConfig(
          {
              "browsers": {
                  "chrome-stable-default": "chrome-stable",
                  "chrome-stable-adb": "adb:chrome",
                  "chrome-stable-adb2": {
                      "path": "chrome",
                      "driver": "adb"
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    self.assertEqual(len(browsers), 3)
    self.assertEqual(browsers[0].label, "chrome-stable-default")
    self.assertEqual(browsers[1].label, "chrome-stable-adb")
    self.assertEqual(browsers[2].label, "chrome-stable-adb2")
    self.assertIsInstance(browsers[0], mock_browser.MockChromeStable)
    self.assertIsInstance(browsers[1], mock_browser.MockChromeAndroidStable)
    self.assertIsInstance(browsers[2], mock_browser.MockChromeAndroidStable)

  def test_flag_combination_invalid(self):
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {
                      "invalid-flag-name": [None, "", "v1"],
                  },
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": ["group1",]
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    message = str(cm.exception)
    self.assertIn("group1", message)
    self.assertIn("invalid-flag-name", message)

  def test_flag_combination_none(self):
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {
                      "--foo": ["None,", "", "v1"],
                  },
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": ["group1"]
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    self.assertIn("None", str(cm.exception))

  def test_flag_combination_duplicate(self):
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {
                      "--duplicate-flag": [None, "", "v1"],
                  },
                  "group2": {
                      "--duplicate-flag": [None, "", "v1"],
                  }
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": ["group1", "group2"]
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    self.assertIn("--duplicate-flag", str(cm.exception))

  def test_empty(self):
    with self.assertRaises(ConfigError):
      BrowserVariantsConfig({"other": {}}, args=self.mock_args).variants
    with self.assertRaises(ConfigError):
      BrowserVariantsConfig({"browsers": {}}, args=self.mock_args).variants

  def test_unknown_group(self):
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": ["unknown-flag-group"]
                  }
              }
          },
          args=self.mock_args).variants
    self.assertIn("unknown-flag-group", str(cm.exception))

  def test_duplicate_group(self):
    with self.assertRaises(ConfigError):
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {}
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": ["group1", "group1"]
                  }
              }
          },
          args=self.mock_args).variants

  def test_non_list_group(self):
    BrowserVariantsConfig(
        {
            "flags": {
                "group1": {}
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": "group1"
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args).variants
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {}
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": 1
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    self.assertIn("chrome-stable", str(cm.exception))
    self.assertIn("flags", str(cm.exception))

    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {}
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": {
                          "group1": True
                      }
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args).variants
    self.assertIn("chrome-stable", str(cm.exception))
    self.assertIn("flags", str(cm.exception))

  def test_duplicate_flag_variant_value(self):
    with self.assertRaises(ConfigError) as cm:
      BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {
                      "--flag": ["repeated", "repeated"]
                  }
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": "group1",
                  }
              }
          },
          args=self.mock_args).variants
    self.assertIn("group1", str(cm.exception))
    self.assertIn("--flag", str(cm.exception))

  def test_unknown_path(self):
    with self.assertRaises(Exception):
      BrowserVariantsConfig(
          {
              "browsers": {
                  "chrome-stable": {
                      "path": "path/does/not/exist",
                  }
              }
          },
          args=self.mock_args).variants
    with self.assertRaises(Exception):
      BrowserVariantsConfig(
          {
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-unknown",
                  }
              }
          },
          args=self.mock_args).variants

  def test_flag_combination_simple(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "group1": {
                    "--foo": [None, "", "v1"],
                }
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": ["group1"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    browsers = config.variants
    self.assertEqual(len(browsers), 3)
    for browser in browsers:
      assert isinstance(browser, mock_browser.MockChromeStable)
      self.assertDictEqual(browser.js_flags.to_dict(), {})
    self.assertDictEqual(browsers[0].flags.to_dict(), {})
    self.assertDictEqual(browsers[1].flags.to_dict(), {"--foo": None})
    self.assertDictEqual(browsers[2].flags.to_dict(), {"--foo": "v1"})

  def test_flag_list(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "group1": [
                    "",
                    "--foo",
                    "-foo=v1",
                ]
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": ["group1"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    browsers = config.variants
    self.assertEqual(len(browsers), 3)
    for browser in browsers:
      assert isinstance(browser, mock_browser.MockChromeStable)
      self.assertDictEqual(browser.js_flags.to_dict(), {})
    self.assertDictEqual(browsers[0].flags.to_dict(), {})
    self.assertDictEqual(browsers[1].flags.to_dict(), {"--foo": None})
    self.assertDictEqual(browsers[2].flags.to_dict(), {"-foo": "v1"})

  def test_flag_combination(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "group1": {
                    "--foo": [None, "", "v1"],
                    "--bar": [None, "", "v1"],
                }
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": ["group1"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    self.assertEqual(len(config.variants), 3 * 3)

  def test_flag_combination_mixed_inline(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "compile-hints-experiment": {
                    "--enable-features": [None, "ConsumeCompileHints"]
                }
            },
            "browsers": {
                "chrome-release": {
                    "path": "chrome-stable",
                    "flags": ["--no-sandbox", "compile-hints-experiment"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    browsers = config.variants
    self.assertEqual(len(browsers), 2)
    self.assertListEqual(["--no-sandbox"], list(browsers[0].flags))
    self.assertListEqual(
        ["--no-sandbox", "--enable-features=ConsumeCompileHints"],
        list(browsers[1].flags))

  def test_flag_single_inline(self):
    config = BrowserVariantsConfig(
        {
            "browsers": {
                "chrome-release": {
                    "path": "chrome-stable",
                    "flags": "--no-sandbox",
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    browsers = config.variants
    self.assertEqual(len(browsers), 1)
    self.assertListEqual(["--no-sandbox"], list(browsers[0].flags))

  def test_flag_combination_mixed_fixed(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "compile-hints-experiment": {
                    "--no-sandbox": "",
                    "--enable-features": [None, "ConsumeCompileHints"]
                }
            },
            "browsers": {
                "chrome-release": {
                    "path": "chrome-stable",
                    "flags": "compile-hints-experiment"
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    browsers = config.variants
    self.assertEqual(len(browsers), 2)
    self.assertListEqual(["--no-sandbox"], list(browsers[0].flags))
    self.assertListEqual(
        ["--no-sandbox", "--enable-features=ConsumeCompileHints"],
        list(browsers[1].flags))

  def test_conflicting_chrome_features(self):
    with self.assertRaises(ConfigError) as cm:
      _ = BrowserVariantsConfig(
          {
              "flags": {
                  "compile-hints-experiment": {
                      "--enable-features": [None, "ConsumeCompileHints"]
                  }
              },
              "browsers": {
                  "chrome-release": {
                      "path":
                          "chrome-stable",
                      "flags": [
                          "--disable-features=ConsumeCompileHints",
                          "compile-hints-experiment"
                      ]
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args)
    msg = str(cm.exception)
    self.assertIn("ConsumeCompileHints", msg)

  def test_no_flags(self):
    config = BrowserVariantsConfig(
        {
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                },
                "chrome-dev": {
                    "path": "chrome-dev",
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    self.assertEqual(len(config.variants), 2)
    browser_0 = config.variants[0]
    assert isinstance(browser_0, mock_browser.MockChromeStable)
    self.assertEqual(browser_0.app_path,
                     mock_browser.MockChromeStable.mock_app_path())
    browser_1 = config.variants[1]
    assert isinstance(browser_1, mock_browser.MockChromeDev)
    self.assertEqual(browser_1.app_path,
                     mock_browser.MockChromeDev.mock_app_path())

  def test_custom_driver(self):
    chromedriver = pth.LocalPath("path/to/chromedriver")
    variants_config = {
        "browsers": {
            "chrome-stable": {
                "browser": "chrome-stable",
                "driver": str(chromedriver),
            }
        }
    }
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      BrowserVariantsConfig(
          copy.deepcopy(variants_config),
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args)
    self.assertIn(str(chromedriver), str(cm.exception))

    self.fs.create_file(chromedriver, st_size=100)
    with mock.patch.object(
        BrowserVariantsConfig,
        "_get_browser_cls",
        return_value=mock_browser.MockChromeStable):
      config = BrowserVariantsConfig(
          variants_config,
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args)
    self.assertTrue(variants_config["browsers"]["chrome-stable"])
    self.assertEqual(len(config.variants), 1)
    browser_0 = config.variants[0]
    assert isinstance(browser_0, mock_browser.MockChromeStable)
    self.assertEqual(browser_0.app_path,
                     mock_browser.MockChromeStable.mock_app_path())

  def test_inline_flags(self):
    with mock.patch.object(
        ChromeWebDriver, "_extract_version",
        return_value="101.22.333.44"), mock.patch.object(
            Chrome,
            "stable_path",
            return_value=mock_browser.MockChromeStable.mock_app_path()):

      config = BrowserVariantsConfig(
          {
              "browsers": {
                  "stable": {
                      "path": "chrome-stable",
                      "flags": ["--foo=bar"]
                  }
              }
          },
          args=self.mock_args)
      self.assertEqual(len(config.variants), 1)
      browser = config.variants[0]
      # TODO: Fix once app lookup is cleaned up
      self.assertEqual(browser.app_path,
                       mock_browser.MockChromeStable.mock_app_path())
      self.assertEqual(browser.version, "101.22.333.44")
      self.assertEqual(browser.flags["--foo"], "bar")

  def test_inline_load_safari(self):
    if not plt.PLATFORM.is_macos:
      return
    with mock.patch.object(Safari, "_extract_version", return_value="16.0"):
      config = BrowserVariantsConfig(
          {"browsers": {
              "safari": {
                  "path": "safari",
              }
          }}, args=self.mock_args)
      self.assertEqual(len(config.variants), 1)

  def test_flag_combination_with_fixed(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "group1": {
                    "--foo": [None, "", "v1"],
                    "--bar": [None, "", "w1"],
                    "--always_1": "true",
                    "--always_2": "true",
                    "--always_3": "true",
                }
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": ["group1"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    self.assertEqual(len(config.variants), 3 * 3)
    for browser in config.variants:
      assert isinstance(browser, mock_browser.MockChromeStable)
      self.assertEqual(browser.app_path,
                       mock_browser.MockChromeStable.mock_app_path())
      expected_flags = (
          "--always_1=true --always_2=true --always_3=true",
          "--bar --always_1=true --always_2=true --always_3=true",
          "--bar=w1 --always_1=true --always_2=true --always_3=true",
          "--foo --always_1=true --always_2=true --always_3=true",
          "--foo --bar --always_1=true --always_2=true --always_3=true",
          "--foo --bar=w1 --always_1=true --always_2=true --always_3=true",
          "--foo=v1 --always_1=true --always_2=true --always_3=true",
          "--foo=v1 --bar --always_1=true --always_2=true --always_3=true",
          "--foo=v1 --bar=w1 --always_1=true --always_2=true --always_3=true",
      )
    self.verify_variant_flags(config.variants, expected_flags)

  def verify_variant_flags(self, variants, expected_flags):
    self.assertEqual(len(variants), len(expected_flags))
    for index, browser in enumerate(variants):
      self.assertEqual(
          str(browser.flags), expected_flags[index],
          f"Unexpected flags for variant[{index}]")

  def test_flag_combination_js_flags_with_fixed(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "group1": {
                    "--js-flags": [
                        None, "--max-opt=1,--trace-ic", "--max-opt=2 --log-all"
                    ],
                },
                "group2": {
                    "default": "--bar=v1 --foo=w2"
                }
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": ["group1", "group2"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    self.assertEqual(len(config.variants), 3)
    for browser in config.variants:
      assert isinstance(browser, mock_browser.MockChromeStable)
      self.assertEqual(browser.app_path,
                       mock_browser.MockChromeStable.mock_app_path())
    expected_flags = (
        "--bar=v1 --foo=w2",
        "--bar=v1 --foo=w2 --js-flags=--max-opt=1,--trace-ic",
        "--bar=v1 --foo=w2 --js-flags=--max-opt=2,--log-all",
    )
    self.verify_variant_flags(config.variants, expected_flags)

  def test_flag_combination_js_flags_combinations_invalid(self):
    with self.assertRaises(ConfigError) as cm:
      _ = BrowserVariantsConfig(
          {
              "flags": {
                  "group1": {
                      "--js-flags": [
                          None, "--max-opt=2,--trace-ic",
                          "--max-opt=3 --log-all"
                      ],
                  },
                  "group2": {
                      "default": "--js-flags=--no-sparkplug"
                  }
              },
              "browsers": {
                  "chrome-stable": {
                      "path": "chrome-stable",
                      "flags": ["group1", "group2"]
                  }
              }
          },
          browser_lookup_override=self.browser_lookup,
          args=self.mock_args)
    self.assertIn("--js-flags", str(cm.exception))

  def test_flag_group_combination(self):
    config = BrowserVariantsConfig(
        {
            "flags": {
                "group1": {
                    "--foo": [None, "", "v1"],
                },
                "group2": {
                    "--bar": [None, "", "w1"],
                },
                "group3": {
                    "--other": ["x1", "x2"],
                }
            },
            "browsers": {
                "chrome-stable": {
                    "path": "chrome-stable",
                    "flags": ["group1", "group2", "group3"]
                }
            }
        },
        browser_lookup_override=self.browser_lookup,
        args=self.mock_args)
    self.assertEqual(len(config.variants), 3 * 3 * 2)
    expected_flags = (
        "--other=x1",
        "--other=x2",
        "--bar --other=x1",
        "--bar --other=x2",
        "--bar=w1 --other=x1",
        "--bar=w1 --other=x2",
        "--foo --other=x1",
        "--foo --other=x2",
        "--foo --bar --other=x1",
        "--foo --bar --other=x2",
        "--foo --bar=w1 --other=x1",
        "--foo --bar=w1 --other=x2",
        "--foo=v1 --other=x1",
        "--foo=v1 --other=x2",
        "--foo=v1 --bar --other=x1",
        "--foo=v1 --bar --other=x2",
        "--foo=v1 --bar=w1 --other=x1",
        "--foo=v1 --bar=w1 --other=x2",
    )
    self.verify_variant_flags(config.variants, expected_flags)

  def test_from_cli_args_browser_config(self):
    if self.platform.is_win:
      self.skipTest("No auto-download available on windows")
    browser_cls = mock_browser.MockChromeStable
    # TODO: migrate to with_stem once python 3.9 is available everywhere
    suffix = browser_cls.mock_app_path().suffix
    browser_bin = browser_cls.mock_app_path().with_name(
        f"Custom Google Chrome{suffix}")
    browser_cls.setup_bin(self.fs, browser_bin, "Chrome")
    config_data = {"browsers": {"chrome-stable": {"path": str(browser_bin),}}}
    config_file = pth.LocalPath("config.hjson")
    with config_file.open("w", encoding="utf-8") as f:
      hjson.dump(config_data, f)

    args = mock.Mock(
        network=NetworkConfig.default(),
        browser=None,
        browser_config=config_file,
        driver_path=None)
    with mock.patch.object(
        BrowserVariantsConfig, "_get_browser_cls", return_value=browser_cls):
      config = BrowserVariantsConfig.from_cli_args(args)
    self.assertEqual(len(config.variants), 1)
    browser = config.variants[0]
    self.assertIsInstance(browser, browser_cls)
    self.assertEqual(browser.app_path, browser_bin)

  def test_from_cli_args_browser(self):
    if self.platform.is_win:
      self.skipTest("No auto-download available on windows")
    browser_cls = mock_browser.MockChromeStable
    # TODO: migrate to with_stem once python 3.9 is available everywhere
    suffix = browser_cls.mock_app_path().suffix
    browser_bin = browser_cls.mock_app_path().with_name(
        f"Custom Google Chrome{suffix}")
    browser_cls.setup_bin(self.fs, browser_bin, "Chrome")
    args = mock.Mock(
        network=NetworkConfig.default(),
        browser=[
            BrowserConfig(browser_bin),
        ],
        browser_config=None,
        enable_features=None,
        disable_features=None,
        driver_path=None,
        js_flags=None,
        other_browser_args=[])
    with mock.patch.object(
        BrowserVariantsConfig, "_get_browser_cls", return_value=browser_cls):
      config = BrowserVariantsConfig.from_cli_args(args)
    self.assertEqual(len(config.variants), 1)
    browser = config.variants[0]
    self.assertIsInstance(browser, browser_cls)
    self.assertEqual(browser.app_path, browser_bin)

  def test_from_cli_args_browser_additional_flags(self):
    browser_cls = mock_browser.MockChromeStable
    args = mock.Mock(
        network=NetworkConfig.default(),
        browser=[
            BrowserConfig.parse_str("chrome"),
        ],
        browser_config=None,
        driver_path=None,
        enable_features="feature_on",
        disable_features="feature_off",
        js_flags=None,
        other_browser_args=["--no-sandbox", "--enable-logging=stderr"])
    with mock.patch.object(
        BrowserVariantsConfig, "_get_browser_cls", return_value=browser_cls):
      config = BrowserVariantsConfig.from_cli_args(args)
    self.assertEqual(len(config.variants), 1)
    browser = config.variants[0]
    self.assertIsInstance(browser, browser_cls)
    self.assertFalse(browser.js_flags)
    self.assertEqual(browser.flags["--enable-features"], "feature_on")
    self.assertEqual(browser.flags["--disable-features"], "feature_off")
    self.assertIn("--no-sandbox", browser.flags)
    self.assertEqual(browser.flags["--enable-logging"], "stderr")

  def test_from_cli_args_browser_js_flags(self):
    browser_cls = mock_browser.MockChromeStable
    args = mock.Mock(
        network=NetworkConfig.default(),
        browser=[
            BrowserConfig.parse_str("chrome"),
        ],
        browser_config=None,
        driver_path=None,
        enable_features=None,
        disable_features=None,
        js_flags=["--max-opt=1"],
        other_browser_args=[])
    with mock.patch.object(
        BrowserVariantsConfig, "_get_browser_cls", return_value=browser_cls):
      config = BrowserVariantsConfig.from_cli_args(args)
    self.assertEqual(len(config.variants), 1)
    browser = config.variants[0]
    self.assertIsInstance(browser, browser_cls)
    self.assertEqual(browser.js_flags.to_dict(), {"--max-opt": "1"})

  def test_from_cli_args_browser_extra_browser_js_flags(self):
    browser_cls = mock_browser.MockChromeStable
    args = mock.Mock(
        network=NetworkConfig.default(),
        browser=[
            BrowserConfig.parse_str("chrome"),
        ],
        browser_config=None,
        driver_path=None,
        enable_features=None,
        disable_features=None,
        js_flags=[],
        other_browser_args=["--js-flags=--max-opt=1,--log-all"])
    with mock.patch.object(
        BrowserVariantsConfig, "_get_browser_cls", return_value=browser_cls):
      config = BrowserVariantsConfig.from_cli_args(args)
    self.assertEqual(len(config.variants), 1)
    browser = config.variants[0]
    self.assertIsInstance(browser, browser_cls)
    self.assertEqual(browser.js_flags.to_dict(), {
        "--max-opt": "1",
        "--log-all": None
    })

  def test_from_cli_args_browser_multiple_js_flags(self):
    browser_cls = mock_browser.MockChromeStable
    args = mock.Mock(
        network=NetworkConfig.default(),
        browser=[
            BrowserConfig.parse_str("chrome"),
        ],
        browser_config=None,
        driver_path=None,
        enable_features="feature_on",
        disable_features="feature_off",
        js_flags=["--max-opt=1", "--max-opt=2,--log-all"],
        other_browser_args=["--no-sandbox", "--enable-logging=stderr"])
    with mock.patch.object(
        BrowserVariantsConfig, "_get_browser_cls", return_value=browser_cls):
      config = BrowserVariantsConfig.from_cli_args(args)
    self.assertEqual(len(config.variants), 2)
    browser_0 = config.variants[0]
    self.assertIsInstance(browser_0, browser_cls)
    self.assertEqual(browser_0.js_flags.to_dict(), {"--max-opt": "1"})
    browser_1 = config.variants[1]
    self.assertIsInstance(browser_1, browser_cls)
    self.assertEqual(browser_1.js_flags.to_dict(), {
        "--max-opt": "2",
        "--log-all": None
    })

    for browser in config.variants:
      self.assertEqual(browser.flags["--enable-features"], "feature_on")
      self.assertEqual(browser.flags["--disable-features"], "feature_off")
      self.assertIn("--no-sandbox", browser.flags)
      self.assertEqual(browser.flags["--enable-logging"], "stderr")

  def test_from_cli_args_browser_config_network_override(self):
    ts_proxy_path = pth.LocalPath("/tsproxy/tsproxy.py")
    self.fs.create_file(ts_proxy_path, st_size=100)
    browser_config_dict = {
        "browsers": {
            "default-network": {
                "path": "chrome-stable",
                "network": "default"
            },
            "default": "chrome-stable",
            "custom-network": {
                "path": "chrome-stable",
                "network": "4G"
            }
        }
    }
    config_file = pth.LocalPath("browsers.config.json")
    with config_file.open("w") as f:
      json.dump(browser_config_dict, f)
    network_3g = NetworkConfig.parse("3G-slow")
    network_4g = NetworkConfig.parse("4G")
    self.assertNotEqual(network_3g.speed.in_kbps, network_4g.speed.in_kbps)
    args = mock.Mock(
        browser=None,
        browser_config=config_file,
        network=network_3g,
        enable_features=None,
        disable_features=None,
        driver_path=None,
        js_flags=None,
        other_browser_args=[])

    with mock.patch.object(
        BrowserVariantsConfig,
        "_get_browser_cls",
        return_value=mock_browser.MockChromeStable
    ), mock.patch(
        "crossbench.network.traffic_shaping.ts_proxy.TsProxyFinder") as finder:
      finder.return_value = mock.Mock(path=ts_proxy_path)
      config = BrowserVariantsConfig.from_cli_args(args,)
    self.assertEqual(len(config.variants), 3)
    browser_1, browser_2, browser_3 = config.variants  # pylint: disable=unbalanced-tuple-unpacking
    # Browser 1 provides an explicit default override:
    self.assertTrue(browser_1.network.is_live)
    self.assertTrue(browser_1.network.traffic_shaper.is_live)
    # Browser 2: uses the default --network:
    self.assertTrue(browser_2.network.is_live)
    self.assertFalse(browser_2.network.traffic_shaper.is_live)
    self.assertEqual(browser_2.network.traffic_shaper._ts_proxy._in_kbps,
                     network_3g.speed.in_kbps)
    # Browser 3; Uses an explicit 4G override:
    self.assertTrue(browser_3.network.is_live)
    self.assertFalse(browser_3.network.traffic_shaper.is_live)
    self.assertEqual(browser_3.network.traffic_shaper._ts_proxy._in_kbps,
                     network_4g.speed.in_kbps)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
