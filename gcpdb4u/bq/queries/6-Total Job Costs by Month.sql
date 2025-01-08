/*
6. Monthly Insights: Total Job Costs by Month
This query calculates the total estimated costs by month to identify spending trends.
*/
SELECT
  EXTRACT(YEAR FROM creation_time) AS year,
  EXTRACT(MONTH FROM creation_time) AS month,
  ROUND(SUM(total_bytes_processed) / POWER(1024, 4), 2) AS total_data_processed_in_tb,
  ROUND(SUM(total_bytes_processed * 5) / POWER(1024, 4), 2) AS estimated_cost_in_usd
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  EXTRACT(YEAR FROM creation_time) = EXTRACT(YEAR FROM CURRENT_DATE()) - 1
  AND state = 'DONE'
GROUP BY
  year, month
ORDER BY
  year, month;
