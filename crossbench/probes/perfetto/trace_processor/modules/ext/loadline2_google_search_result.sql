INCLUDE PERFETTO MODULE ext.first_presentation_time;

CREATE OR REPLACE PERFETTO FUNCTION loadline2_google_search_result_score()
RETURNS FLOAT
AS
SELECT
  -- Multiply by 60 to make the score per minutes rather than per second.
  60e9 / (
    get_lcp_presentation_time('https://www.google.com/search?q=cats')
    - get_event_time('LoadLine2/*/google_search_result_start'));

