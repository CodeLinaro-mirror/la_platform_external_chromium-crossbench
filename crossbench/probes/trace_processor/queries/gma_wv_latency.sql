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
  )

SELECT
  'click_' || init_slices.rn AS instance,
  init_slices.dur / 1000000.0 as 'CUI_NAME_WEBVIEW_INITIALIZATION_ms',
  load_slices.dur / 1000000.0 as 'CUI_NAME_CREATIVE_WEBVIEW_LOAD_ms',
  (init_slices.dur + load_slices.dur) / 1000000.0 AS 'creative_wv_latency_ms',
  sdk_init_slice.dur / 1000000.0 as 'CUI_NAME_SDKINIT_ms',
  load_ad_slice.dur / 1000000.0 as 'loadAd()_ms',
  (sdk_init_slice.dur + load_ad_slice.dur) / 1000000.0 as 'first_total_latency_ms'
FROM init_slices
JOIN load_slices ON init_slices.rn = load_slices.rn
LEFT JOIN sdk_init_slice on init_slices.rn = sdk_init_slice.rn
LEFT JOIN load_ad_slice on sdk_init_slice.rn = load_ad_slice.rn
ORDER BY init_slices.rn ASC;
