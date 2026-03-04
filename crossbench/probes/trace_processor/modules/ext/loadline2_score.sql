-- Copyright 2025 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.
INCLUDE PERFETTO MODULE chrome.loadline_2;

DROP TABLE IF EXISTS loadline2_score;
CREATE PERFETTO TABLE loadline2_score as
SELECT
  page || '_visual' AS metric,
  60e9 / (visual_presentation - story_start) AS value
FROM chrome_loadline2_stages
UNION ALL
SELECT
  page || '_interactive' AS metric,
  60e9 / (interactive_presentation - story_start) AS value
FROM chrome_loadline2_stages;
