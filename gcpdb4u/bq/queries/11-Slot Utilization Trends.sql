/*
Slot usage per reservation, helping monitor efficiency and capacity planning.
*/
SELECT
  reservation_id,
  ROUND(SUM(total_slot_ms) / (1000 * 60 * 60), 2) AS total_slot_time_in_hours,
  COUNT(*) AS total_jobs
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  EXTRACT(YEAR FROM creation_time) = EXTRACT(YEAR FROM CURRENT_DATE()) - 1
  AND state = 'DONE'
  AND reservation_id IS NOT NULL
GROUP BY
  reservation_id
ORDER BY
  total_slot_time_in_hours DESC;
