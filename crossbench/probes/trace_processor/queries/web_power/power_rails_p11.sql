INCLUDE PERFETTO MODULE android.power_rails;

DROP VIEW IF EXISTS per_rail;

CREATE VIEW per_rail AS
SELECT
  power_rail_name,
  (MAX(value) - MIN(value)) / (MAX(ts) - MIN(ts)) * 1e6 AS avg_power_mw
FROM android_power_rails_counters
WHERE
  -- This set of rails approximates kibble data as closely as possible with
  -- ODPM.
  -- It is specific to Pixel 11.
  power_rail_name IN (
    'power.S5M_VDD_DSU_uws',
    'power.S11M_VDD_DSU_M_uws',
    'power.S13M_VDD_CPU0_uws',
    'power.S3M_VDD_CPU1_uws',
    'power.S2M_VDD_CPU2_uws',
    'power.S1M_VDD_AMB_uws',
    'power.S8S_VDD_GMC_uws',
    'power.S4S_VDD2H_MEM_uws',
    'power.S5S_VDDQ_MEM_uws',
    'power.S9S_VDD_INFRA_uws',
    'power.S4M_VDD_AUR_uws',
    'power.S7M_VDD_TPU_uws',
    'power.S1S_VDD_MM_uws',
    'power.S2S_VDD_GPU_uws',
    'power.S9M_VDD_AOSS_uws',
    'power.S10M_VDD_AOSS_OD_uws',
    'power.S6M_LLDO1_uws',
    'power.S8M_LLDO2_uws',
    'power.S3S_LLDO1_uws',
    'power.S6S_LLDO2_uws',
    'power.S7S_MLDO_uws',
    'power.S10S_VDD_INFRA_MM_GPU_AUR_M_uws'
  )
GROUP BY 1;

SELECT
  power_rail_name,
  avg_power_mw
FROM per_rail
ORDER BY 1;
