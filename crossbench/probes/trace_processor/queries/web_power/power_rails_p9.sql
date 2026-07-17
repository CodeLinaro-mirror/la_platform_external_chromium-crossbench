-- Copyright 2026 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

INCLUDE PERFETTO MODULE android.power_rails;

DROP VIEW IF EXISTS measured_interval;
CREATE VIEW measured_interval AS
SELECT
  (SELECT ts FROM slice WHERE name = 'crossbench-web-power-start' LIMIT 1) AS start_ts,
  (SELECT ts FROM slice WHERE name = 'crossbench-web-power-stop' LIMIT 1) AS end_ts;

DROP VIEW IF EXISTS per_rail;

CREATE VIEW per_rail AS
SELECT
  power_rail_name,
  (MAX(value) - MIN(value)) / (MAX(ts) - MIN(ts)) * 1e6 AS avg_power_mw
FROM android_power_rails_counters
WHERE ts >= COALESCE(
        (SELECT start_ts FROM measured_interval),
        (SELECT MIN(ts) FROM android_power_rails_counters))
  AND ts <= COALESCE(
        (SELECT end_ts FROM measured_interval),
        (SELECT MAX(ts) FROM android_power_rails_counters))
  AND power_rail_name IN (
    -- Main, ext
    -- 'power.rails.camera',
    -- 'power.rails.display',
    -- 'power.rails.radio.frontend',

    -- Main, int
    'power.rails.cpu.big',
    'power.rails.cpu.little',
    'power.rails.cpu.mid',
    'power.rails.cpu.mid.mem',
    'power.rails.ldo.main.a',
    'power.rails.ldo.main.b',
    'power.rails.memory.interface',
    'power.rails.system.fabric',
    'power.rails.tpu',

    -- Sub, ext
    -- 'power.rails.mmwave',
    -- 'power.rails.modem',
    -- 'power.rails.wifi.bt',

    -- Sub, int
    'power.rails.aoc.logic',
    'power.rails.ddr.a',
    'power.rails.ddr.b',
    'power.rails.ddr.c',
    'power.rails.gpu',
    'power.rails.ldo.sub',
    'power.rails.multimedia',
    'power.rails.udfps',
    'power.rails.ufs'
  )
GROUP BY 1;

SELECT
  power_rail_name,
  avg_power_mw
FROM per_rail
ORDER BY 1;
