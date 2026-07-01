-- Copyright 2025 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

INCLUDE PERFETTO MODULE sql_packages.memory_pressure.iterations;

DROP TABLE IF EXISTS tabs_alive;

CREATE TABLE tabs_alive AS
WITH raw_slices AS (
  SELECT
    s.ts AS page_loaded_ts,
    s.track_id,
    EXTRACT_ARG(s.arg_set_id, 'debug.data.detail') AS detail_json
  FROM slice AS s
  WHERE s.cat = 'blink.user_timing' AND s.name = 'tabs_alive'
)
SELECT
  CAST(json_extract(r.detail_json, '$.tab_index') AS INTEGER) AS tab_index,
  r.page_loaded_ts,
  p.pid,
  p.name AS process_name,
  CAST(json_extract(r.detail_json, '$.alive_count') AS INTEGER) AS alive_tabs
FROM raw_slices AS r
JOIN thread_track AS tt
  ON r.track_id = tt.id
JOIN thread AS t
  USING (utid)
JOIN process AS p
  USING (upid);

DROP TABLE IF EXISTS alive_tabs_by_tab_index;

CREATE TABLE alive_tabs_by_tab_index AS
SELECT
  iterations.id AS it_id,
  tabs_alive.tab_index,
  tabs_alive.alive_tabs,
  tabs_alive.pid,
  tabs_alive.process_name
FROM iterations
JOIN tabs_alive
  ON tabs_alive.page_loaded_ts >= iterations.start
  AND tabs_alive.page_loaded_ts <= iterations.end;

DROP TABLE IF EXISTS average_alive_tabs_after_first_kill;

CREATE TABLE average_alive_tabs_after_first_kill AS
SELECT
  iterations.id AS it_id,
  CAST(json_extract(EXTRACT_ARG(s.arg_set_id, 'debug.data.detail'), '$.tab_index_at_first_kill') AS INTEGER) AS tab_index_at_first_kill,
  CAST(json_extract(EXTRACT_ARG(s.arg_set_id, 'debug.data.detail'), '$.average_alive_tabs_after_first_kill') AS REAL) AS average_alive_tabs_after_first_kill
FROM slice AS s
JOIN iterations ON s.ts >= iterations.start AND s.ts <= iterations.end
WHERE s.cat = 'blink.user_timing' AND s.name = 'crossbench_avg_tabs_alive';
