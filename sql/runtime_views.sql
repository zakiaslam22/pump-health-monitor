-- query 1
CREATE OR REPLACE VIEW runtime_summary AS
WITH totals AS (
    SELECT
        COUNT(*)            AS failures,
        SUM(duration_hours) AS downtime_hours,
        AVG(duration_hours) AS avg_outage_hours,
        MAX(duration_hours) AS longest_outage_hours,
        MIN(duration_hours) AS shortest_outage_hours,
        EXTRACT(EPOCH FROM (TIMESTAMP '2018-09-01 00:00' - TIMESTAMP '2018-04-01 00:00')) / 3600 AS total_hours
    FROM events
)
SELECT
    failures,
    ROUND(total_hours::numeric, 0) AS total_hours,
    ROUND(downtime_hours::numeric, 1) AS total_downtime_hours,
    ROUND((100 * (1 - downtime_hours / total_hours))::numeric, 2) AS uptime_pct,
    ROUND(avg_outage_hours::numeric, 1) AS avg_outage_hours,
    longest_outage_hours,
    shortest_outage_hours
FROM totals;

--query 2
CREATE OR REPLACE VIEW time_between_failures AS
WITH gaps AS (
    SELECT
        event_id,
        start_time,
        LAG(end_time) OVER (ORDER BY start_time) AS previous_end
    FROM events
)
SELECT
    event_id,
    previous_end,
    start_time,
    ROUND((EXTRACT(EPOCH FROM (start_time - previous_end)) / 3600)::numeric, 2) AS hours_since_last_failure
FROM gaps;


-- query 3
CREATE OR REPLACE VIEW mtbf_summary AS
SELECT
    ROUND(AVG(hours_since_last_failure), 2)      AS mtbf_hours,
    ROUND(AVG(hours_since_last_failure) / 24, 1) AS mtbf_days,
    COUNT(hours_since_last_failure)              AS gaps_counted
FROM time_between_failures;

