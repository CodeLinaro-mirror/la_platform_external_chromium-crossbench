// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

function __dismissBanners() {
  'use strict';

  // The following values will be injected by the caller.
  const ELEMENT_TYPE = INJECTED_TYPE;
  const ELEMENT_ROLE = INJECTED_ROLE;
  const ELEMENT_TEXT = INJECTED_TEXT;

  self.__DISMISS_BANNERS_INJECTED = true;

  const findAndClick = (observer) => {
    const links = Array.from(
        document.querySelectorAll(`${ELEMENT_TYPE}[role="${ELEMENT_ROLE}"]`));
    const link = links.find(el => el.textContent.trim() === ELEMENT_TEXT);

    if (!link) {
      return false;
    }

    link.click();
    if (observer) {
      observer.disconnect();
    }
    return true;
  };

  if (!findAndClick(null)) {
    const observer =
        new MutationObserver((mutations, obs) => { findAndClick(obs); });
    observer.observe(document.documentElement,
                     {childList : true, subtree : true});
  }
}

if (typeof self === 'object' && self) {
  if (self.__DISMISS_BANNERS_INJECTED) {
    // Script already injected.
  } else {
    // Call it immediately; the observer handles the waiting.
    __dismissBanners();
  }
} else {
  // Environment lacks 'self' global (e.g. Node.js); skipping overrides.
}
