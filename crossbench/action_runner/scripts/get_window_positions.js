// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// See get_window_positions.js.README.md for an explanation of this script.

let bottom_inset = 0;
let inset_probe = null;
if (window.screenY === 0 && window.outerHeight === screen.height) {
  const cache = window.__crossbench_inset_cache;
  if (cache && cache.outerH === window.outerHeight &&
      cache.innerH === window.visualViewport.height) {
    bottom_inset = cache.value;
  } else {
    inset_probe = document.createElement('div');
    inset_probe.style.cssText =
        'position:fixed;top:0;left:0;width:0;visibility:hidden;' +
        'pointer-events:none;contain:layout style paint;' +
        'height:calc(env(safe-area-max-inset-bottom, 0px) - ' +
        'env(safe-area-inset-bottom, 0px))';
    document.documentElement.appendChild(inset_probe);
  }
}

let element_rect;
const found_element = Boolean(arguments[0] && element);
if (found_element) {
  if (arguments[1]) {
    element.scrollIntoView({block: 'nearest'});
  }
  element_rect = element.getBoundingClientRect();
} else {
  element_rect = new DOMRect();
}

if (inset_probe) {
  bottom_inset = inset_probe.getBoundingClientRect().height;
  inset_probe.remove();
  window.__crossbench_inset_cache = {
    outerH: window.outerHeight,
    innerH: window.visualViewport.height,
    value: bottom_inset,
  };
}
const outer_height = window.outerHeight - bottom_inset;

return [
  found_element, window.devicePixelRatio, window.outerWidth, outer_height,
  window.visualViewport.width, window.visualViewport.height, screen.width,
  screen.height, screen.availWidth, screen.availHeight, screenX, screenY,
  element_rect.left, element_rect.top, element_rect.width, element_rect.height
];
