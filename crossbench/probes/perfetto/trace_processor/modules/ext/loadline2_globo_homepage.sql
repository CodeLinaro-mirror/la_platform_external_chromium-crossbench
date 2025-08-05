INCLUDE PERFETTO MODULE ext.first_presentation_time;

CREATE OR REPLACE PERFETTO FUNCTION loadline2_globo_homepage_score_visual()
RETURNS FLOAT
AS
SELECT
  -- Multiply by 60 to make the score per minutes rather than per second.
  60e9 / (
    get_presentation_time('LoadLine2/globo_homepage/headline_shown')
    - get_event_time('LoadLine2/phone/globo_homepage_start'));

CREATE OR REPLACE PERFETTO FUNCTION loadline2_globo_homepage_score_interactive()
RETURNS FLOAT
AS
SELECT
  -- Multiply by 60 to make the score per minutes rather than per second.
  60e9 / (
    get_presentation_time('LoadLine2/globo_homepage/cookie_banner_gone')
    - get_event_time('LoadLine2/phone/globo_homepage_start'));
