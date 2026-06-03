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
    'power.rails.cpu.little',
    'power.rails.cpu.mid',
    'power.rails.cpu.big',
    'power.rails.cpu.mid.mem',
    'power.rails.gpu',
    'power.rails.display',
    'power.rails.multimedia',
    'power.rails.memory.interface',
    'power.rails.system.fabric',
    'power.rails.ddr.a',
    'power.rails.ddr.b',
    'power.rails.ddr.c',
    'power.rails.ldo.main.a',
    'power.rails.ldo.main.b',
    'power.rails.ldo.sub',
    'power.rails.camera',
    'power.rails.modem',
    'power.rails.tpu',
    'power.rails.ufs',
    'power.rails.wifi.bt',
    'power.rails.aoc.logic',
    'power.S12S_VDD_AUR_uws'
  )
GROUP BY 1;

SELECT
  power_rail_name,
  avg_power_mw
FROM per_rail
ORDER BY 1;
