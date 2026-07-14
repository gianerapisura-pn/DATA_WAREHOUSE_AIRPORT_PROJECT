SELECT
    d.year,
    d.half_year,
    d.quarter,
    d.month,
    t.source_type,
    COUNT(*) AS transaction_count,
    SUM(t.total_amount) AS total_sales
FROM mart_passenger_ticket t
JOIN dim_date d ON d.date_key = t.date_key
GROUP BY ROLLUP (d.year, d.half_year, d.quarter, d.month, t.source_type)
ORDER BY d.year, d.half_year, d.quarter, d.month, t.source_type;

SELECT
    d.year,
    d.quarter,
    d.month,
    t.source_type,
    COUNT(*) AS transaction_count,
    SUM(t.total_amount) AS total_sales,
    GROUPING(d.year) AS grouped_year,
    GROUPING(d.quarter) AS grouped_quarter,
    GROUPING(d.month) AS grouped_month,
    GROUPING(t.source_type) AS grouped_source
FROM mart_passenger_ticket t
JOIN dim_date d ON d.date_key = t.date_key
GROUP BY CUBE (d.year, d.quarter, d.month, t.source_type)
ORDER BY d.year, d.quarter, d.month, t.source_type;
