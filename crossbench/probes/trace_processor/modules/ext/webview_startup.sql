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
  s.name LIKE '%WebViewChromiumAwInit.startChromiumLockedAsync_task1%'
  OR s.name LIKE '%WebViewChromiumAwInit.startChromiumLockedSync%'
LIMIT 1;

DROP VIEW IF EXISTS webview_startup_end_slice;
CREATE VIEW webview_startup_end_slice AS
SELECT (ts + dur) as end_ts
FROM slice
WHERE
  name LIKE '%WebViewChromiumAwInit.startChromiumLockedAsync_task5%'
  OR name LIKE '%WebViewChromiumAwInit.startChromiumLockedSync%'
LIMIT 1;
