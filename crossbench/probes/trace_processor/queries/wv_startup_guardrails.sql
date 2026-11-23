-- Copyright 2026 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

WITH
  stage1_timeline AS (
    SELECT dur / 1000000.0 AS dur_ms
    FROM slice
    WHERE
      category = 'android_webview.timeline'
      AND name = 'WebView.Startup.CreationTime.Stage1.FactoryInit'
      AND dur > 0
    ORDER BY ts ASC
    LIMIT 1
  ),
  start_cl_timeline AS (
    SELECT dur / 1000000.0 AS dur_ms
    FROM slice
    WHERE
      category = 'android_webview.timeline'
      AND name = 'WebView.Startup.CreationTime.StartChromiumLocked'
      AND dur > 0
    ORDER BY ts ASC
    LIMIT 1
  )
SELECT
  stage1_timeline.dur_ms AS "Android.WebView.Startup.CreationTime.Stage1.FactoryInit_mean",
  start_cl_timeline.dur_ms AS "Android.WebView.Startup.CreationTime.StartChromiumLocked_mean"
FROM stage1_timeline, start_cl_timeline;
