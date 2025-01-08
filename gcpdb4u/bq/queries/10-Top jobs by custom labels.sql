/*
Highlights top jobs by custom labels.
Helps identify high-cost or inefficient jobs tagged to specific teams or environments.
*/
SELECT
  COALESCE((SELECT value FROM UNNEST(labels) WHERE key = 'team' LIMIT 1), 'Unlabeled') AS team,
  COALESCE((SELECT value FROM UNNEST(labels) WHERE key = 'environment' LIMIT 1), 'Unlabeled') AS environment,
  job_type,
  ROUND(total_bytes_processed / POWER(1024, 4), 2) AS data_processed_in_tb,
  ROUND(total_slot_ms / (1000 * 60), 2) AS slot_time_in_minutes,
  TIMESTAMP_DIFF(end_time, start_time, SECOND) AS duration_in_sec
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  EXTRACT(YEAR FROM creation_time) = EXTRACT(YEAR FROM CURRENT_DATE()) - 1
  AND state = 'DONE'
  --AND team !=  NULL
ORDER BY
  data_processed_in_tb DESC
LIMIT 10;
