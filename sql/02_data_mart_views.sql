CREATE OR REPLACE VIEW vw_ticket_data_mart AS
SELECT
    source_type,
    transaction_id,
    transaction_date,
    passenger_id,
    passenger_name,
    passenger_email,
    loyalty_status,
    flight_key,
    airline_key,
    airline_name,
    origin_airport_code,
    origin_airport_name,
    origin_city,
    destination_airport_code,
    destination_airport_name,
    destination_city,
    aircraft_type,
    ticket_price,
    taxes,
    baggage_fees,
    total_amount,
    flight_status,
    delay_minutes,
    is_eligible,
    eligibility_reason
FROM mart_passenger_ticket;

CREATE OR REPLACE VIEW vw_sales_hierarchy AS
SELECT
    year,
    quarter,
    half_year,
    month,
    month_name,
    source_type,
    transaction_count,
    total_sales,
    average_ticket_value,
    delayed_count,
    cancelled_count
FROM mart_sales_summary;

CREATE OR REPLACE VIEW vw_current_passengers AS
SELECT
    passenger_sk,
    passenger_id,
    full_name,
    email,
    loyalty_status,
    effective_from
FROM dim_passenger
WHERE is_current = TRUE;

CREATE OR REPLACE VIEW vw_passenger_scd_history AS
SELECT
    passenger_sk,
    passenger_id,
    full_name,
    email,
    loyalty_status,
    effective_from,
    effective_to,
    is_current
FROM dim_passenger;
