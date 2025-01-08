/*
4. Average and Total Slot Time by Job Type
This query provides insights into slot usage by job type, helping analyze resource consumption.
*/
SELECT
  job_type,
  ROUND(SUM(total_slot_ms) / (1000 * 60 * 60), 2) AS total_slot_time_in_hours,
  ROUND(AVG(total_slot_ms) / 1000, 2) AS avg_slot_time_in_sec
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  EXTRACT(YEAR FROM creation_time) = EXTRACT(YEAR FROM CURRENT_DATE()) - 1
  AND state = 'DONE'
GROUP BY
  job_type
ORDER BY
  total_slot_time_in_hours DESC;
