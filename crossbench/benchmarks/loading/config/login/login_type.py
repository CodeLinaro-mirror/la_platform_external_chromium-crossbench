# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import enum
from typing import TYPE_CHECKING, Final

from crossbench.benchmarks.loading.config.login.google import GoogleLogin
from crossbench.benchmarks.loading.config.login.google_os import GoogleOsLogin
from crossbench.config import ConfigEnum

if TYPE_CHECKING:
  from crossbench.benchmarks.loading.config.login.base import BaseLoginBlock


@enum.unique
class LoginType(ConfigEnum):
  GOOGLE = ("google", "Login for google properties")
  GOOGLE_OS = (
    "google-os",
    "Provision OS Google account and link browser profile",
  )


LOGIN_LOOKUP: Final[dict[LoginType, type[BaseLoginBlock]]] = {
  LoginType.GOOGLE: GoogleLogin,
  LoginType.GOOGLE_OS: GoogleOsLogin,
}
