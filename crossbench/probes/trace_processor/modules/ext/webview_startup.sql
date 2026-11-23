-- Copyright 2026 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

DROP VIEW IF EXISTS webview_startup_start_slice;
CREATE VIEW webview_startup_start_slice AS
SELECT ts, tt.utid, t.upid
FROM slice s
JOIN
  thread_track tt
  ON s.track_id = tt.id
JOIN
  thread t
  ON tt.utid = t.utid
WHERE
  s.dur >= 0
  AND (
    s.name GLOB '*WebViewChromiumAwInit.startChromiumLockedAsync_task1/*'
    OR s.name GLOB '*WebViewChromiumAwInit.startChromiumLockedSync*'
  )
ORDER BY s.ts ASC, s.dur DESC
LIMIT 1;

DROP VIEW IF EXISTS webview_startup_end_slice;
CREATE VIEW webview_startup_end_slice AS
SELECT (s.ts + s.dur) AS end_ts
FROM slice s
JOIN
  thread_track tt
  ON s.track_id = tt.id
JOIN
  webview_startup_start_slice start_slice
  ON tt.utid = start_slice.utid
WHERE
  s.dur >= 0
  AND s.ts >= start_slice.ts
  AND (
    s.name GLOB '*WebViewChromiumAwInit.startChromiumLockedSync*'
    OR (
      s.name GLOB '*WebViewChromiumAwInit.startChromiumLockedAsync_task[0-9]*/[0-9]*'
      AND STR_SPLIT(
        STR_SPLIT(
          s.name,
          'WebViewChromiumAwInit.startChromiumLockedAsync_task',
          1
        ),
        '/',
        0
      ) = STR_SPLIT(
        STR_SPLIT(
          s.name,
          'WebViewChromiumAwInit.startChromiumLockedAsync_task',
          1
        ),
        '/',
        1
      )
    )
  )
ORDER BY end_ts DESC
LIMIT 1;
