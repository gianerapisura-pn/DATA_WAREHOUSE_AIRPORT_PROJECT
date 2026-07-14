SELECT 'dim_date' AS table_name, COUNT(*) AS row_count FROM dim_date
UNION ALL SELECT 'dim_airline', COUNT(*) FROM dim_airline
UNION ALL SELECT 'dim_airport', COUNT(*) FROM dim_airport
UNION ALL SELECT 'dim_passenger', COUNT(*) FROM dim_passenger
UNION ALL SELECT 'dim_flight', COUNT(*) FROM dim_flight
UNION ALL SELECT 'fact_corporate_sales', COUNT(*) FROM fact_corporate_sales
UNION ALL SELECT 'fact_agency_sales', COUNT(*) FROM fact_agency_sales
UNION ALL SELECT 'mart_passenger_ticket', COUNT(*) FROM mart_passenger_ticket;

SELECT COUNT(*) AS corporate_total_mismatches
FROM fact_corporate_sales
WHERE ROUND(ticket_price + taxes + baggage_fees, 2) <> ROUND(total_amount, 2);

SELECT COUNT(*) AS agency_total_mismatches
FROM fact_agency_sales
WHERE ROUND(ticket_price + taxes + baggage_fees, 2) <> ROUND(total_amount, 2);

SELECT passenger_id, COUNT(*) AS versions
FROM dim_passenger
GROUP BY passenger_id
HAVING COUNT(*) > 1
ORDER BY passenger_id;

SELECT year, quarter, half_year, month, source_type, total_sales
FROM mart_sales_summary
ORDER BY year, month, source_type;
