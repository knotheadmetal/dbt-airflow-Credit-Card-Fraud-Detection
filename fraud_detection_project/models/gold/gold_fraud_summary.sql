{{ config(materialized='table') }}

-- Gold layer: Business-ready aggregated data
SELECT 
    -- Time dimensions
    DATE(transaction_timestamp) as transaction_date,
    hour_of_day,
    day_of_week,
    
    -- Amount dimensions
    amount_category,
    risk_level,
    
    -- Metrics
    COUNT(*) as total_transactions,
    SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_transactions,
    SUM(CASE WHEN is_fraud THEN 0 ELSE 1 END) as legitimate_transactions,
    
    -- Fraud rate
    ROUND(
        SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::NUMERIC / COUNT(*)::NUMERIC * 100, 
        4
    ) as fraud_rate_percent,
    
    -- Amount metrics
    AVG(amount) as avg_amount,
    AVG(CASE WHEN is_fraud THEN amount END) as avg_fraud_amount,
    AVG(CASE WHEN NOT is_fraud THEN amount END) as avg_legitimate_amount,
    
    SUM(amount) as total_amount,
    SUM(CASE WHEN is_fraud THEN amount ELSE 0 END) as total_fraud_amount,
    SUM(CASE WHEN NOT is_fraud THEN amount ELSE 0 END) as total_legitimate_amount,
    
    -- Feature statistics for key fraud indicators
    AVG(ABS(v4)) as avg_abs_v4,
    AVG(ABS(v11)) as avg_abs_v11,
    AVG(ABS(v14)) as avg_abs_v14,
    
    CURRENT_TIMESTAMP as aggregated_at
    
FROM {{ ref('silver_transactions') }}
GROUP BY 
    DATE(transaction_timestamp),
    hour_of_day,
    day_of_week,
    amount_category,
    risk_level

