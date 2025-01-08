/*
Breaks down resource usage and costs by custom labels (e.g., team, environment).
Enables cost and resource attribution to specific workflows, teams, or environments.
*/
SELECT
  COALESCE((SELECT value FROM UNNEST(labels) WHERE key = 'team' LIMIT 1), 'Unlabeled') AS team,
  COALESCE((SELECT value FROM UNNEST(labels) WHERE key = 'environment' LIMIT 1), 'Unlabeled') AS environment,
  job_type,
  ROUND(SUM(total_bytes_processed) / POWER(1024, 4), 2) AS total_data_processed_in_tb, -- Convert bytes to TB
  ROUND(SUM(total_bytes_processed * 5) / POWER(1024, 4), 2) AS estimated_cost_in_usd, -- Estimated cost ($5 per TB)
  COUNT(*) AS total_jobs,
  ROUND(SUM(total_slot_ms) / (1000 * 60 * 60), 2) AS total_slot_time_in_hours -- Slot time in hours
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  EXTRACT(YEAR FROM creation_time) = EXTRACT(YEAR FROM CURRENT_DATE()) - 1 -- Last year's data
  AND state = 'DONE'
GROUP BY
  team, environment, job_type
ORDER BY
  total_data_processed_in_tb DESC;
