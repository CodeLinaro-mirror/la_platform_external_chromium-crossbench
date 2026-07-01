-- Copyright 2025 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

INCLUDE PERFETTO MODULE sql_packages.memory_pressure.iterations;

DROP VIEW IF EXISTS tab_timing_by_tab_index;

CREATE VIEW tab_timing_by_tab_index AS
SELECT
  iterations.id AS it_id,
  CAST(json_extract(EXTRACT_ARG(s.arg_set_id, 'debug.data.detail'), '$.tab_index') AS INTEGER) AS tab_index,
  CAST(json_extract(EXTRACT_ARG(s.arg_set_id, 'debug.data.detail'), '$.page_load_duration_ms') AS REAL) AS page_load_duration_ms,
  CAST(json_extract(EXTRACT_ARG(s.arg_set_id, 'debug.data.detail'), '$.allocation_duration_ms') AS REAL) AS allocation_duration_ms
FROM slice AS s
JOIN iterations ON s.ts >= iterations.start AND s.ts <= iterations.end
WHERE s.cat = 'blink.user_timing' AND s.name = 'crossbench_tab_timing';
