/*
1. Total Data Processed and Job Count by Month and Job Type
This query helps identify how much data is being processed and the volume of jobs for each job type on a monthly basis.
*/
SELECT
  EXTRACT(YEAR FROM creation_time) AS year,
  EXTRACT(MONTH FROM creation_time) AS month,
  job_type,
  ROUND(SUM(total_bytes_processed) / POWER(1024, 4), 2) AS total_data_processed_in_tb,
  COUNT(*) AS total_jobs
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  EXTRACT(YEAR FROM creation_time) = EXTRACT(YEAR FROM CURRENT_DATE()) - 1
  AND state = 'DONE'
GROUP BY
  year, month, job_type
ORDER BY
  year, month, job_type;
