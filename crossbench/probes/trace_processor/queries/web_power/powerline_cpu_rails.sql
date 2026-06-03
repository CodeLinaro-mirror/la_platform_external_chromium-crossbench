-- Copyright 2026 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

-- For Google Pixel devices, this query query estimates the power consumed
-- during a PowerLine run using go/pixel-odpm-rails. It includes all rails
-- associated with the SoC compute logic (CPU, GPU, memory etc), but excludes
-- radios, displays etc.
INCLUDE PERFETTO MODULE android.power_rails;

DROP VIEW IF EXISTS measured_interval;
CREATE VIEW measured_interval AS
SELECT
  (SELECT ts FROM slice WHERE name = 'crossbench-web-power-start' LIMIT 1) AS start_ts,
  (SELECT ts FROM slice WHERE name = 'crossbench-web-power-stop' LIMIT 1) AS end_ts;

SELECT
  SUM(energy_delta) as total_energy,
  power_rail_name
FROM android_power_rails_counters
WHERE ts >= COALESCE(
        (SELECT start_ts FROM measured_interval),
        (SELECT MIN(ts) FROM android_power_rails_counters))
  AND ts <= COALESCE(
        (SELECT end_ts FROM measured_interval),
        (SELECT MAX(ts) FROM android_power_rails_counters))
  AND power_rail_name LIKE '%CPU%'
  AND power_rail_name NOT LIKE '%CPU%_M%'
GROUP BY power_rail_name
ORDER BY total_energy DESC;
