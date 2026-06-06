-- models/marts/mart_time_series_features.sql
-- This mart model calculates rolling averages, lag variables, and seasonality metrics 
-- for machine learning consumption (e.g., XGBoost).

WITH staging AS (
    SELECT * FROM {{ ref('stg_metrics__raw_data') }}
),

-- Aggregate to hourly level in case there were multiple readings per hour
hourly_aggregated AS (
    SELECT
        metric_hour,
        metric_name,
        AVG(metric_value) AS avg_hourly_value
    FROM staging
    GROUP BY 1, 2
),

feature_engineering AS (
    SELECT
        metric_hour,
        metric_name,
        avg_hourly_value AS target_value,
        
        -- Time-based Features (Seasonality)
        EXTRACT(HOUR FROM metric_hour) AS hour_of_day,
        EXTRACT(ISODOW FROM metric_hour) AS day_of_week,
        EXTRACT(DAY FROM metric_hour) AS day_of_month,
        
        -- Lag Variables (e.g., value 1 hour ago, 24 hours ago)
        LAG(avg_hourly_value, 1) OVER (PARTITION BY metric_name ORDER BY metric_hour) AS lag_1h_value,
        LAG(avg_hourly_value, 24) OVER (PARTITION BY metric_name ORDER BY metric_hour) AS lag_24h_value,
        LAG(avg_hourly_value, 168) OVER (PARTITION BY metric_name ORDER BY metric_hour) AS lag_7d_value,
        
        -- Rolling Averages (e.g., 24-hour moving average)
        AVG(avg_hourly_value) OVER (
            PARTITION BY metric_name 
            ORDER BY metric_hour 
            ROWS BETWEEN 24 PRECEDING AND 1 PRECEDING
        ) AS rolling_avg_24h,
        
        -- Rolling Standard Deviation (useful for anomaly detection/Z-score)
        STDDEV(avg_hourly_value) OVER (
            PARTITION BY metric_name 
            ORDER BY metric_hour 
            ROWS BETWEEN 24 PRECEDING AND 1 PRECEDING
        ) AS rolling_stddev_24h

    FROM hourly_aggregated
)

SELECT * FROM feature_engineering
-- Filter out the initial rows where lag variables and rolling averages are null
-- depending on modeling requirements, though often handled in the ML pipeline.
-- WHERE lag_168h_value IS NOT NULL
