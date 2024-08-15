// Copyright 2024 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

const headline_text_id = 'maincontent'

const observer = new MutationObserver(mutations => {
  performance.mark('update');
  const headline = document.getElementById(headline_text_id)
  if (!headline) {
    return
  }
  performance.mark('maincontent.created');
});


if (window.location ==
    'https://edition.cnn.com/2024/04/21/china/china-spy-agency-public-profile-intl-hnk/index.html') {
  observer.observe(document, {childList: true, subtree: true});
}
