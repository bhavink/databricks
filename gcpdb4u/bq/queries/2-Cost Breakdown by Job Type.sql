/*
2. Cost Breakdown by Job Type
This query calculates the estimated cost for each job type based on data processed. For on-demand queries, it assumes a cost of $5 per TB.
*/
SELECT
  job_type,
  ROUND(SUM(total_bytes_processed) / POWER(1024, 4), 2) AS total_data_processed_in_tb,
  ROUND(SUM(total_bytes_processed * 5) / POWER(1024, 4), 2) AS estimated_cost_in_usd
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  EXTRACT(YEAR FROM creation_time) = EXTRACT(YEAR FROM CURRENT_DATE()) - 1
  AND state = 'DONE'
GROUP BY
  job_type
ORDER BY
  estimated_cost_in_usd DESC;
