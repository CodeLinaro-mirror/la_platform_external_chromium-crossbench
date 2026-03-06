-- Copyright 2026 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

-- Export the full profile to pprof.

DROP VIEW IF EXISTS cb_pprof_spans;

CREATE VIEW cb_pprof_spans AS
SELECT
  ts,
  utid,
  callsite_id
FROM
  perf_sample
UNION ALL
SELECT
  ts,
  utid,
  callsite_id
FROM
  instruments_sample;

SELECT
  'profile.pprof' AS file_name,
  WRITE_FILE(
    'profile.pprof',
    (
      SELECT
        EXPERIMENTAL_PROFILE(
          CAT_STACKS(
            'profile',
            IFNULL(p.name, 'Unknown Process'),
            IFNULL(t.name, 'Unknown Thread'),
            STACK_FROM_STACK_PROFILE_CALLSITE(callsite_id)
          ),
          'samples',
          'count',
          1
        ) AS profile
      FROM
        cb_pprof_spans s
        LEFT JOIN thread t ON s.utid = t.utid
        LEFT JOIN process p ON t.upid = p.upid
    )
  );
