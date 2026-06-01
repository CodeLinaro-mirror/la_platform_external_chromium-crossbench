INCLUDE PERFETTO MODULE android.power_rails;

DROP VIEW IF EXISTS per_rail;

CREATE VIEW per_rail AS
SELECT
  power_rail_name,
  (MAX(value) - MIN(value)) / (MAX(ts) - MIN(ts)) * 1e6 AS avg_power_mw
FROM android_power_rails_counters
WHERE
  power_rail_name IN (
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
