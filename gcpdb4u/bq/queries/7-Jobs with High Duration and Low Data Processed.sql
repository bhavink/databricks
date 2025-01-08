/*
7. Inefficient Jobs: Jobs with High Duration and Low Data Processed
This query highlights inefficient jobs with high runtime but low data processed, which could signal optimization opportunities.
*/


SELECT
  job_type,
  user_email,
  TIMESTAMP_DIFF(end_time, start_time, SECOND) AS duration_in_sec,
  ROUND(total_bytes_processed / POWER(1024, 4), 2) AS data_processed_in_tb,
  query
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  EXTRACT(YEAR FROM creation_time) = EXTRACT(YEAR FROM CURRENT_DATE()) - 1
  AND state = 'DONE'
  AND TIMESTAMP_DIFF(end_time, start_time, SECOND) > 300 -- Jobs running longer than 5 minutes
  AND total_bytes_processed < POWER(1024, 3) -- Jobs processing less than 1 GB
ORDER BY
  duration_in_sec DESC
LIMIT 10;
