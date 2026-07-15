-- Copyright 2026 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

DROP TABLE IF EXISTS loadline2_browser_info;
CREATE PERFETTO TABLE loadline2_browser_info AS
SELECT
  str_value AS browser_version,
  1 AS placeholder_value
FROM metadata WHERE name LIKE '%product-version%' LIMIT 1;
