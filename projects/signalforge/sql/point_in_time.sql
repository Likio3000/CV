WITH requests AS (
    SELECT json_extract(value, '$.request_id') AS request_id,
           json_extract(value, '$.machine_id') AS machine_id,
           json_extract(value, '$.prediction_time') AS prediction_time
    FROM json_each(:requests)
), ranked AS (
    SELECT q.request_id, q.machine_id, q.prediction_time,
           r.reading_id, r.event_time, r.available_at,
           r.temperature_milli_c, r.vibration_milli_mm_s,
           ROW_NUMBER() OVER (
               PARTITION BY q.request_id
               ORDER BY r.event_time DESC, r.available_at DESC, r.reading_id DESC
           ) AS rank
    FROM requests q LEFT JOIN readings r
      ON r.machine_id = q.machine_id
     AND r.event_time <= q.prediction_time
     AND r.available_at <= q.prediction_time
     AND r.event_time >= q.prediction_time - :ttl
)
SELECT request_id, machine_id, prediction_time, reading_id, event_time, available_at,
       temperature_milli_c, vibration_milli_mm_s,
       CASE WHEN reading_id IS NOT NULL THEN 'ready'
            WHEN EXISTS (
                SELECT 1 FROM readings known
                WHERE known.machine_id = ranked.machine_id
                  AND known.event_time <= ranked.prediction_time
                  AND known.available_at <= ranked.prediction_time
            ) THEN 'expired'
            ELSE 'no_known_reading' END AS status
FROM ranked WHERE rank = 1 ORDER BY request_id;
