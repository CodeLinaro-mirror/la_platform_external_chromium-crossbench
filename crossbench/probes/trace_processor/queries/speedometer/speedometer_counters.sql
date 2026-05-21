-- Copyright 2026 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

-- Speedometer counter delta analysis.
-- Computes the delta for all available performance counter tracks
-- during the scoring parts of the Speedometer run.
INCLUDE PERFETTO MODULE chrome.speedometer;

-- Select all performance counters.
DROP VIEW IF EXISTS speedometer_counters_of_interest;

CREATE VIEW speedometer_counters_of_interest AS
SELECT
  c.*,
  0 AS dur,
  pct.cpu AS cpu,
  pct.name AS counter_name
FROM counter AS c
JOIN perf_counter_track AS pct
  ON c.track_id = pct.id;

-- Replicate the speedometer intervals for every track to enable partitioning
-- by track_id.
DROP VIEW IF EXISTS speedometer_measure_by_track;

CREATE VIEW speedometer_measure_by_track AS
SELECT
  m.*,
  t.id AS track_id
FROM chrome_speedometer_measure AS m,
  (
    SELECT id
    FROM perf_counter_track
  ) AS t;

-- Span join the counters with speedometer intervals partitioned by track_id.
DROP TABLE IF EXISTS speedometer_counters_joined;

CREATE VIRTUAL TABLE speedometer_counters_joined
USING SPAN_JOIN(
  speedometer_counters_of_interest PARTITIONED track_id,
  speedometer_measure_by_track PARTITIONED track_id
);

-- Compute the delta for each continuous block.
DROP VIEW IF EXISTS speedometer_counter_delta;

CREATE VIEW speedometer_counter_delta AS
SELECT
  MAX(value) - MIN(value) AS delta,
  suite_name,
  test_name,
  measure_type,
  iteration,
  cpu,
  counter_name
FROM speedometer_counters_joined
GROUP BY
  suite_name,
  test_name,
  measure_type,
  iteration,
  cpu,
  counter_name;

-- Group and sum up counters per suite and counter name.
SELECT
  SUM(delta) AS value,
  counter_name,
  suite_name
FROM speedometer_counter_delta
GROUP BY
  suite_name,
  counter_name
UNION ALL
SELECT
  SUM(delta) AS value,
  counter_name,
  'Total' AS suite_name
FROM speedometer_counter_delta
GROUP BY
  counter_name
ORDER BY
  suite_name,
  counter_name;
