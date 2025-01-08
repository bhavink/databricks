/*
5. User Accountability: Jobs Run and Data Processed Per User
This query identifies the top users consuming BigQuery resources by total data processed and job count.
*/
SELECT
  user_email,
  job_type,
  COUNT(*) AS total_jobs,
  ROUND(SUM(total_bytes_processed) / POWER(1024, 4), 2) AS total_data_processed_in_tb,
  ROUND(SUM(total_bytes_processed * 5) / POWER(1024, 4), 2) AS estimated_cost_in_usd
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  EXTRACT(YEAR FROM creation_time) = EXTRACT(YEAR FROM CURRENT_DATE()) - 1
  AND state = 'DONE'
GROUP BY
  user_email, job_type
ORDER BY
  total_data_processed_in_tb DESC
LIMIT 10;
