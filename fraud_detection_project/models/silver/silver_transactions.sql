{{ config(materialized='table') }}

-- Silver layer: Cleaned and enriched data
WITH enriched_transactions AS (
    SELECT 
        *,
        -- Convert time_seconds to timestamp
        TIMESTAMP '2023-09-01 00:00:00' + INTERVAL '1 second' * time_seconds as transaction_timestamp,
        
        -- Extract time features
        EXTRACT(HOUR FROM (TIMESTAMP '2023-09-01 00:00:00' + INTERVAL '1 second' * time_seconds)) as hour_of_day,
        EXTRACT(DOW FROM (TIMESTAMP '2023-09-01 00:00:00' + INTERVAL '1 second' * time_seconds)) as day_of_week,
        
        -- Amount categories
        CASE 
            WHEN amount < 10 THEN 'micro'
            WHEN amount < 100 THEN 'small'
            WHEN amount < 1000 THEN 'medium'
            ELSE 'large'
        END as amount_category,
        
        -- Fraud flag
        CASE WHEN class = 1 THEN TRUE ELSE FALSE END as is_fraud,
        
        -- Risk score based on key features (V4, V11, V14)
        CASE 
            WHEN ABS(v4) > 3 OR ABS(v11) > 3 OR ABS(v14) > 3 THEN 'high'
            WHEN ABS(v4) > 2 OR ABS(v11) > 2 OR ABS(v14) > 2 THEN 'medium'
            ELSE 'low'
        END as risk_level
        
    FROM {{ ref('bronze_transactions') }}
)

SELECT 
    time_seconds,
    transaction_timestamp,
    hour_of_day,
    day_of_week,
    v1, v2, v3, v4, v5, v6, v7, v8, v9, v10,
    v11, v12, v13, v14, v15, v16, v17, v18, v19, v20,
    v21, v22, v23, v24, v25, v26, v27, v28,
    amount,
    amount_category,
    class,
    is_fraud,
    risk_level,
    loaded_at
FROM enriched_transactions

