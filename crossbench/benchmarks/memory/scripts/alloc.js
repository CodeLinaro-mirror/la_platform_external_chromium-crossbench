// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

function alloc(sizeMB, randomRatio) {
  const PAGE_SIZE = 4096;
  const FLOAT64_BYTES = 8;
  const FLOAT64_PER_PAGE = PAGE_SIZE / FLOAT64_BYTES;
  const MB = 1024 * 1024;
  const totalCount = sizeMB * MB / FLOAT64_BYTES;
  const randomCount = FLOAT64_PER_PAGE * randomRatio;

  // Using Float64Array as each element of Float64Array should consume 64
  // bits memory.
  const array = new Float64Array(totalCount);
  for (let i = 0; i < array.length; i++) {
    if (i % FLOAT64_PER_PAGE < randomCount) {
      array[i] = Math.random();
    } else {
      array[i] = 0.0;
    }
  }
  return array;
}

const pageLoadedTs = performance.now();

const allocMb = TARGET_MB;

const startTime = new Date();
const allocStartTs = performance.now();

// Assigns the content to document to avoid optimization of unused data.
document.out = alloc(allocMb, .67);

const allocEndTs = performance.now();
const ellapse = (new Date() - startTime) / 1000;

// Shows the loading time for manual test.
const content = "Allocating " + allocMb + " MB takes " + ellapse + " seconds";
document.getElementsByTagName('body')[0].textContent = content;

// Create the marks after the allocation to work around the issue where marks
// created too early after a process starts are dropped.
performance.mark("page-load~TAB_INDEX", {
  startTime: 0,
});
performance.mark("page-loaded~TAB_INDEX", {
  startTime: pageLoadedTs,
});
performance.mark("allocation-start~TAB_INDEX", {
  startTime: allocStartTs,
});
performance.mark("allocation-done~TAB_INDEX", {
  startTime: allocEndTs,
});
