INCLUDE PERFETTO MODULE ext.first_presentation_time;

CREATE OR REPLACE PERFETTO FUNCTION loadline2_google_doc_score()
RETURNS FLOAT
AS
SELECT
  -- Multiply by 60 to make the score per minutes rather than per second.
  60e9 / (
    get_lcp_presentation_time('https://docs.google.com/document/d/13AWeOGqtSkfpPK7meqE_X-GQQggwx4JJ1vc0YGvKg34/edit#heading=h.gjdgxs')
    - get_event_time('LoadLine2/tablet/google_doc_start'));

