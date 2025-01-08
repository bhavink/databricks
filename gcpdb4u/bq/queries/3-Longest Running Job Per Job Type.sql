/*
3. Longest Running Job Per Job Type
This query identifies the longest running job for each job type, including the user who ran it, the job duration, and the amount of data processed.
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
QUALIFY ROW_NUMBER() OVER (PARTITION BY job_type ORDER BY TIMESTAMP_DIFF(end_time, start_time, SECOND) DESC) = 1;
