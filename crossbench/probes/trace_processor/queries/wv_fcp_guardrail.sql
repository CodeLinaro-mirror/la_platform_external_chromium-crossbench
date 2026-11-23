-- Copyright 2026 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

SELECT
  AVG(dur / 1000000.0)
    AS "PageLoad.PaintTiming.NavigationToFirstContentfulPaint_mean"
FROM slice
WHERE
  name = 'PageLoadMetrics.NavigationToFirstContentfulPaint'
  AND dur > 0
HAVING COUNT(*) > 0;
