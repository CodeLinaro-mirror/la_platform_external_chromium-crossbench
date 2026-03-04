WITH
  init_slices AS (
    -- Get the duration for webview initialization
    SELECT
      s.name,
      s.dur,
      s.ts,
      ROW_NUMBER() OVER (ORDER BY s.ts ASC) AS rn
    FROM slice s
    WHERE s.name = 'CUI_NAME_WEBVIEW_INITIALIZATION'
    ORDER BY s.ts ASC
  ),

  load_slices as (
    -- Get the duration for creative webview load
    SELECT
      s.name,
      s.dur,
      s.ts,
      ROW_NUMBER() OVER (ORDER BY s.ts ASC) AS rn
    FROM slice s
    WHERE s.name = 'CUI_NAME_CREATIVE_WEBVIEW_LOAD'
    ORDER BY s.ts ASC
  ),

  sdk_init_slice as (
    -- Get the GMA SDK init duration of the first click
    SELECT
      s.name,
      s.dur,
      s.ts,
      ROW_NUMBER() OVER (ORDER BY s.ts ASC) AS rn
    FROM slice s
    WHERE s.name = 'CUI_NAME_SDKINIT'
  ),

  load_ad_slice as (
    -- Get the loadAd() method duration of the first click
    SELECT
      s.name,
      s.dur,
      s.ts,
      ROW_NUMBER() OVER (ORDER BY s.ts ASC) AS rn
    FROM slice s
    WHERE s.name = 'loadAd'
  ),

  per_instance_metrics as (
    -- Join slices by instance index (rn) and calculate latencies in ms
    SELECT
      init_slices.rn AS instance,
      init_slices.dur / 1000000.0 as 'CUI_NAME_WEBVIEW_INITIALIZATION_ms',
      load_slices.dur / 1000000.0 as 'CUI_NAME_CREATIVE_WEBVIEW_LOAD_ms',
      (init_slices.dur + load_slices.dur) / 1000000.0 AS 'creative_wv_latency_ms',
      sdk_init_slice.dur / 1000000.0 as 'CUI_NAME_SDKINIT_ms',
      load_ad_slice.dur / 1000000.0 as 'loadAd_method_ms',
      (sdk_init_slice.dur + load_ad_slice.dur) / 1000000.0 as 'first_total_latency_ms'
    FROM init_slices
    JOIN load_slices ON init_slices.rn = load_slices.rn
    LEFT JOIN sdk_init_slice on init_slices.rn = sdk_init_slice.rn
    LEFT JOIN load_ad_slice on sdk_init_slice.rn = load_ad_slice.rn
    ORDER BY init_slices.rn ASC
  )

-- Flatten the results into a single row for separate metrics for first and second click's latencies.
SELECT
  MAX(CASE WHEN instance = 1 THEN CUI_NAME_WEBVIEW_INITIALIZATION_ms END) AS CUI_NAME_WEBVIEW_INITIALIZATION_ms_1,
  MAX(CASE WHEN instance = 2 THEN CUI_NAME_WEBVIEW_INITIALIZATION_ms END) AS CUI_NAME_WEBVIEW_INITIALIZATION_ms_2,
  MAX(CASE WHEN instance = 1 THEN creative_wv_latency_ms END) AS CUI_NAME_CREATIVE_WEBVIEW_LOAD_ms_1,
  MAX(CASE WHEN instance = 2 THEN creative_wv_latency_ms END) AS CUI_NAME_CREATIVE_WEBVIEW_LOAD_ms_2,
  MAX(CASE WHEN instance = 1 THEN creative_wv_latency_ms END) AS creative_wv_latency_ms_1,
  MAX(CASE WHEN instance = 2 THEN creative_wv_latency_ms END) AS creative_wv_latency_ms_2,
  MAX(CASE WHEN instance = 1 THEN CUI_NAME_SDKINIT_ms END) AS CUI_NAME_SDKINIT_ms,
  MAX(CASE WHEN instance = 1 THEN loadAd_method_ms END) AS loadAd_method_ms,
  MAX(CASE WHEN instance = 1 THEN first_total_latency_ms END) AS first_total_latency_ms
FROM per_instance_metrics;
