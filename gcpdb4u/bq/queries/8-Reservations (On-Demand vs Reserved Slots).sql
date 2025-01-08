/*
Breaks down slot usage into Reserved and On-Demand.
Includes total slot time, job count, data processed, and estimated costs.
*/
SELECT
  IF(reservation_id IS NULL, 'On-Demand', 'Reserved') AS slot_type,
  ROUND(SUM(total_slot_ms) / (1000 * 60 * 60), 2) AS total_slot_time_in_hours,
  COUNT(*) AS total_jobs,
  ROUND(SUM(total_bytes_processed) / POWER(1024, 4), 2) AS total_data_processed_in_tb,
  ROUND(SUM(total_bytes_processed * 5) / POWER(1024, 4), 2) AS estimated_cost_in_usd
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  EXTRACT(YEAR FROM creation_time) = EXTRACT(YEAR FROM CURRENT_DATE()) - 1
  AND state = 'DONE'
GROUP BY
  slot_type
ORDER BY
  slot_type;
