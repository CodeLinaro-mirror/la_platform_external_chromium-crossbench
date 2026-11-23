-- Copyright 2026 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

INCLUDE PERFETTO MODULE ext.webview_startup;

WITH
  startup_window AS (
    SELECT
      start_slice.utid AS utid,
      start_slice.ts AS start_ts,
      end_slice.end_ts AS end_ts
    FROM webview_startup_start_slice AS start_slice
    CROSS JOIN webview_startup_end_slice AS end_slice
    WHERE
      end_slice.end_ts >= start_slice.ts
      AND EXISTS (
        SELECT 1
        FROM thread_state AS ts_check
        WHERE ts_check.utid = start_slice.utid
      )
  )
SELECT
  COALESCE(
    SUM(
      MIN(tsb.ts + tsb.dur, w.end_ts) - MAX(tsb.ts, w.start_ts)
    ),
    0
  ) / 1000000.0 AS D_thread_state_startCL_dur_ms
FROM startup_window AS w
LEFT JOIN thread_state AS tsb
  ON tsb.utid = w.utid
  AND tsb.state = 'D'
  AND tsb.dur > 0
  AND tsb.ts < w.end_ts
  AND (tsb.ts + tsb.dur) > w.start_ts
GROUP BY w.utid;
