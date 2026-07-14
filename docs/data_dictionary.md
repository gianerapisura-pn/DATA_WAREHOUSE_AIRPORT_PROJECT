# Data Dictionary

## `dim_date`

| Column | Meaning |
|---|---|
| `date_key` | Integer date key in `YYYYMMDD` format |
| `full_date` | Calendar date |
| `day_of_month` | Day number |
| `day_name` | Weekday name |
| `day_of_week` | ISO weekday number |
| `month` | Month number |
| `month_name` | Month name |
| `quarter` | Quarter 1-4 |
| `half_year` | Half-year 1-2 |
| `year` | Calendar year |
| `is_weekend` | Weekend indicator |

## `dim_passenger`

| Column | Meaning |
|---|---|
| `passenger_sk` | Warehouse surrogate key |
| `passenger_id` | Stable business/source key after mapping |
| `full_name` | Passenger name |
| `email` | Passenger email |
| `loyalty_status` | Bronze, Silver, Gold, or Platinum |
| `effective_from` | Start of the version |
| `effective_to` | End of the version |
| `is_current` | Current-version flag |
| `record_hash` | Change-detection hash |

## `dim_airline`

| Column | Meaning |
|---|---|
| `airline_sk` | Warehouse surrogate key |
| `airline_key` | Airline business code |
| `airline_name` | Airline name |
| `alliance` | Airline alliance or Independent |
| SCD fields | Historical version fields |

## `dim_airport`

| Column | Meaning |
|---|---|
| `airport_sk` | Warehouse surrogate key |
| `airport_key` | Three-letter airport code |
| `airport_name` | Airport name |
| `city` | Standardized city |
| `country` | Standardized country |
| SCD fields | Historical version fields |

## `dim_flight`

| Column | Meaning |
|---|---|
| `flight_sk` | Warehouse surrogate key |
| `flight_key` | Flight identifier |
| `airline_sk` | Airline dimension key |
| `origin_airport_sk` | Origin airport dimension key |
| `destination_airport_sk` | Destination airport dimension key |
| `aircraft_type` | Aircraft model/type |

## Sales facts

Both fact tables contain:

| Column | Meaning |
|---|---|
| transaction key | Source transaction identifier |
| `date_key` | Transaction date dimension key |
| `passenger_sk` | Passenger version used when the fact was loaded |
| `flight_sk` | Flight dimension key |
| `ticket_price` | Base ticket amount |
| `taxes` | Tax amount |
| `baggage_fees` | Baggage amount |
| `total_amount` | Reconciled sum of the three monetary components |
| `batch_id` | Ingestion batch |
| `source_row` | Original source row number |

## `mart_passenger_ticket`

The check-in data mart combines the sales facts with passenger, flight, airline, airport, date, and flight-status data. It includes the eligibility result and reason.

## `mart_sales_summary`

Monthly aggregate by source type, with quarter and half-year attributes for rollup and cube-style analysis.
