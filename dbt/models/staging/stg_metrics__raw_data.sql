-- models/staging/stg_metrics__raw_data.sql
-- This staging model selects data from the raw Postgres table and does basic cleanup/casting.

WITH source AS (
    -- Assuming a Postgres connection where the database name is not explicitly needed in the FROM clause,
    -- or utilizing a dbt source macro if sources.yml was defined.
    -- For simplicity, selecting directly from the metrics schema:
    SELECT * FROM metrics.raw_data
),

renamed AS (
    SELECT
        id AS metric_id,
        timestamp AS metric_timestamp,
        -- Truncate to hour to allow for hourly aggregations if timestamps were more granular
        DATE_TRUNC('hour', timestamp) AS metric_hour,
        DATE_TRUNC('day', timestamp) AS metric_date,
        metric_name,
        metric_value,
        tags
    FROM source
)

SELECT * FROM renamed
