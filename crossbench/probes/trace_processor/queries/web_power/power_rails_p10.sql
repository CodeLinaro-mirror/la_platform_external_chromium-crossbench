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
WHERE ts >= COALESCE((SELECT start_ts FROM measured_interval), (SELECT MIN(ts) FROM android_power_rails_counters))
  AND ts <= COALESCE((SELECT end_ts FROM measured_interval), (SELECT MAX(ts) FROM android_power_rails_counters))
  AND power_rail_name IN (
    'power.S1M_VDD_AMB_uws',
    'power.S2M_VDD_CPU2_uws',
    'power.S3M_VDD_CPU1_uws',
    'power.S4M_VDD_CPU_uws',
    'power.S5M_VDD_AUR_uws',
    'power.rails.ldo.main.a',
    'power.rails.tpu',
    'power.rails.ldo.main.b',
    'power.S9M_VDD_TPU_M_uws',
    'power.S10M_VDD_AOC_uws',
    'power.S11M_VDD_CPU_M_uws',
    'power.S12M_VDD_CPU1_M_uws',
    'power.S1S_VDD_MM_uws',
    'power.S2S_VDD_GPU_uws',
    'power.rails.ldo.sub',
    'power.rails.ddr.c',
    'power.rails.ddr.a',
    'power.S6S_LLDO2_uws',
    'power.S7S_MLDO_uws',
    'power.S8S_VDD_GMC_uws',
    'power.S9S_VDD_INFRA_uws',
    'power.S10S_VDD_INFRA_MM_GPU_M_uws',
    'power.S11S_UFS_VCC_uws',
    'power.S12S_uws'
  )
GROUP BY 1;

SELECT
  power_rail_name,
  avg_power_mw
FROM per_rail
ORDER BY 1;
