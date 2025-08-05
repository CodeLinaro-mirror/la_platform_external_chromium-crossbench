// Copyright 2025 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

if (window.location.href === 'https://www.google.com/search?q=cats') {
  let complete = false;

  const button_observer = new MutationObserver(mutations => {
    const button = document.querySelector(".tHlp8d");
    const menu = document.querySelector(".cGY8if");

    if (!button || !menu) {
      return;
    }
    button_observer.disconnect();

    const attribute_observer = new MutationObserver(() => {
      if (menu.style.display !== 'none') {
        attribute_observer.disconnect();
        performance.mark('LoadLine2/google_search_result/menu_shown');
        complete = true;
      }
    });
    attribute_observer.observe(menu, {attributes: true});

    click = function() {
      if (complete) return;
      button.click();
      setTimeout(click, 10);
    };
    click();
  });

  const overview_observer = new MutationObserver(unused => {
    if (document.querySelector('.a-no-hover-decoration')) {
      performance.mark('LoadLine2/google_search_result/overview_shown');
      overview_observer.disconnect();
    }
  });

  overview_observer.observe(document, {childList: true, subtree: true});
  button_observer.observe(document, {childList: true, subtree: true});
}
