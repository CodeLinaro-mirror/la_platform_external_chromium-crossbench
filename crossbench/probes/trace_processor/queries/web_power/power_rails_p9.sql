-- Copyright 2026 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

INCLUDE PERFETTO MODULE web_power.web_power_rails;

SELECT
  power_rail_name,
  avg_power_mw
FROM ext_web_power_per_rail
WHERE power_rail_name IN (
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
ORDER BY 1;
