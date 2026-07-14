CREATE EXTENSION IF NOT EXISTS pgcrypto;


CREATE TABLE dim_airline (
	airline_sk SERIAL NOT NULL, 
	airline_key VARCHAR(10) NOT NULL, 
	airline_name VARCHAR(150) NOT NULL, 
	alliance VARCHAR(80) NOT NULL, 
	effective_from TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	effective_to TIMESTAMP WITHOUT TIME ZONE, 
	is_current BOOLEAN NOT NULL, 
	record_hash VARCHAR(64) NOT NULL, 
	PRIMARY KEY (airline_sk), 
	CONSTRAINT uq_airline_version UNIQUE (airline_key, effective_from)
);


CREATE TABLE dim_airport (
	airport_sk SERIAL NOT NULL, 
	airport_key VARCHAR(10) NOT NULL, 
	airport_name VARCHAR(180) NOT NULL, 
	city VARCHAR(100) NOT NULL, 
	country VARCHAR(100) NOT NULL, 
	effective_from TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	effective_to TIMESTAMP WITHOUT TIME ZONE, 
	is_current BOOLEAN NOT NULL, 
	record_hash VARCHAR(64) NOT NULL, 
	PRIMARY KEY (airport_sk), 
	CONSTRAINT uq_airport_version UNIQUE (airport_key, effective_from)
);


CREATE TABLE dim_date (
	date_key INTEGER NOT NULL, 
	full_date DATE NOT NULL, 
	day_of_month INTEGER NOT NULL, 
	day_name VARCHAR(12) NOT NULL, 
	day_of_week INTEGER NOT NULL, 
	month INTEGER NOT NULL, 
	month_name VARCHAR(12) NOT NULL, 
	quarter INTEGER NOT NULL, 
	half_year INTEGER NOT NULL, 
	year INTEGER NOT NULL, 
	is_weekend BOOLEAN NOT NULL, 
	PRIMARY KEY (date_key), 
	UNIQUE (full_date)
);


CREATE TABLE dim_passenger (
	passenger_sk SERIAL NOT NULL, 
	passenger_id VARCHAR(20) NOT NULL, 
	full_name VARCHAR(160) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	loyalty_status VARCHAR(30) NOT NULL, 
	effective_from TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	effective_to TIMESTAMP WITHOUT TIME ZONE, 
	is_current BOOLEAN NOT NULL, 
	record_hash VARCHAR(64) NOT NULL, 
	PRIMARY KEY (passenger_sk), 
	CONSTRAINT uq_passenger_version UNIQUE (passenger_id, effective_from)
);


CREATE TABLE ingestion_batches (
	batch_id SERIAL NOT NULL, 
	dataset_name VARCHAR(60) NOT NULL, 
	source_filename VARCHAR(255) NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	rows_received INTEGER NOT NULL, 
	rows_loaded INTEGER NOT NULL, 
	rows_rejected INTEGER NOT NULL, 
	rows_repaired INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (batch_id)
);


CREATE TABLE mart_passenger_ticket (
	ticket_mart_id SERIAL NOT NULL, 
	source_type VARCHAR(20) NOT NULL, 
	transaction_id INTEGER NOT NULL, 
	date_key INTEGER NOT NULL, 
	transaction_date DATE NOT NULL, 
	passenger_id VARCHAR(20) NOT NULL, 
	passenger_name VARCHAR(160) NOT NULL, 
	passenger_email VARCHAR(255) NOT NULL, 
	loyalty_status VARCHAR(30) NOT NULL, 
	flight_key VARCHAR(20) NOT NULL, 
	airline_key VARCHAR(10) NOT NULL, 
	airline_name VARCHAR(150) NOT NULL, 
	origin_airport_code VARCHAR(10) NOT NULL, 
	origin_airport_name VARCHAR(180) NOT NULL, 
	origin_city VARCHAR(100) NOT NULL, 
	destination_airport_code VARCHAR(10) NOT NULL, 
	destination_airport_name VARCHAR(180) NOT NULL, 
	destination_city VARCHAR(100) NOT NULL, 
	aircraft_type VARCHAR(80) NOT NULL, 
	ticket_price NUMERIC(12, 2) NOT NULL, 
	taxes NUMERIC(12, 2) NOT NULL, 
	baggage_fees NUMERIC(12, 2) NOT NULL, 
	total_amount NUMERIC(12, 2) NOT NULL, 
	flight_status VARCHAR(20) NOT NULL, 
	delay_minutes INTEGER NOT NULL, 
	is_eligible BOOLEAN NOT NULL, 
	eligibility_reason VARCHAR(250) NOT NULL, 
	PRIMARY KEY (ticket_mart_id)
);


CREATE TABLE mart_sales_summary (
	summary_id SERIAL NOT NULL, 
	year INTEGER NOT NULL, 
	quarter INTEGER NOT NULL, 
	half_year INTEGER NOT NULL, 
	month INTEGER NOT NULL, 
	month_name VARCHAR(12) NOT NULL, 
	source_type VARCHAR(20) NOT NULL, 
	transaction_count INTEGER NOT NULL, 
	total_sales NUMERIC(14, 2) NOT NULL, 
	average_ticket_value NUMERIC(14, 2) NOT NULL, 
	delayed_count INTEGER NOT NULL, 
	cancelled_count INTEGER NOT NULL, 
	PRIMARY KEY (summary_id), 
	CONSTRAINT uq_sales_summary_period UNIQUE (year, quarter, half_year, month, source_type)
);


CREATE TABLE dim_flight (
	flight_sk SERIAL NOT NULL, 
	flight_key VARCHAR(20) NOT NULL, 
	airline_sk INTEGER NOT NULL, 
	origin_airport_sk INTEGER NOT NULL, 
	destination_airport_sk INTEGER NOT NULL, 
	aircraft_type VARCHAR(80) NOT NULL, 
	PRIMARY KEY (flight_sk), 
	FOREIGN KEY(airline_sk) REFERENCES dim_airline (airline_sk), 
	FOREIGN KEY(origin_airport_sk) REFERENCES dim_airport (airport_sk), 
	FOREIGN KEY(destination_airport_sk) REFERENCES dim_airport (airport_sk)
);


CREATE TABLE flight_status_events (
	event_id SERIAL NOT NULL, 
	flight_key VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	delay_minutes INTEGER NOT NULL, 
	event_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	source VARCHAR(40) NOT NULL, 
	batch_id INTEGER, 
	PRIMARY KEY (event_id), 
	FOREIGN KEY(batch_id) REFERENCES ingestion_batches (batch_id)
);


CREATE TABLE rejected_records (
	rejection_id SERIAL NOT NULL, 
	batch_id INTEGER NOT NULL, 
	dataset_name VARCHAR(60) NOT NULL, 
	source_row INTEGER NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	raw_data TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (rejection_id), 
	FOREIGN KEY(batch_id) REFERENCES ingestion_batches (batch_id)
);


CREATE TABLE stg_agency_sales (
	staging_id SERIAL NOT NULL, 
	batch_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	transaction_id TEXT, 
	transaction_date TEXT, 
	passenger_id TEXT, 
	flight_key TEXT, 
	ticket_price TEXT, 
	taxes TEXT, 
	baggage_fees TEXT, 
	total_amount TEXT, 
	PRIMARY KEY (staging_id), 
	FOREIGN KEY(batch_id) REFERENCES ingestion_batches (batch_id)
);


CREATE TABLE stg_airlines (
	staging_id SERIAL NOT NULL, 
	batch_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	airline_key TEXT, 
	airline_name TEXT, 
	alliance TEXT, 
	PRIMARY KEY (staging_id), 
	FOREIGN KEY(batch_id) REFERENCES ingestion_batches (batch_id)
);


CREATE TABLE stg_airports (
	staging_id SERIAL NOT NULL, 
	batch_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	airport_key TEXT, 
	airport_name TEXT, 
	city TEXT, 
	country TEXT, 
	PRIMARY KEY (staging_id), 
	FOREIGN KEY(batch_id) REFERENCES ingestion_batches (batch_id)
);


CREATE TABLE stg_corporate_sales (
	staging_id SERIAL NOT NULL, 
	batch_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	transaction_id TEXT, 
	date_key TEXT, 
	passenger_id TEXT, 
	flight_key TEXT, 
	ticket_price TEXT, 
	taxes TEXT, 
	baggage_fees TEXT, 
	total_amount TEXT, 
	PRIMARY KEY (staging_id), 
	FOREIGN KEY(batch_id) REFERENCES ingestion_batches (batch_id)
);


CREATE TABLE stg_flight_events (
	staging_id SERIAL NOT NULL, 
	batch_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	flight_key TEXT, 
	status TEXT, 
	delay_minutes TEXT, 
	event_time TEXT, 
	PRIMARY KEY (staging_id), 
	FOREIGN KEY(batch_id) REFERENCES ingestion_batches (batch_id)
);


CREATE TABLE stg_flights (
	staging_id SERIAL NOT NULL, 
	batch_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	flight_key TEXT, 
	origin_airport_key TEXT, 
	destination_airport_key TEXT, 
	aircraft_type TEXT, 
	PRIMARY KEY (staging_id), 
	FOREIGN KEY(batch_id) REFERENCES ingestion_batches (batch_id)
);


CREATE TABLE stg_passengers (
	staging_id SERIAL NOT NULL, 
	batch_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	passenger_id TEXT, 
	full_name TEXT, 
	email TEXT, 
	loyalty_status TEXT, 
	PRIMARY KEY (staging_id), 
	FOREIGN KEY(batch_id) REFERENCES ingestion_batches (batch_id)
);


CREATE TABLE fact_agency_sales (
	agency_sale_sk SERIAL NOT NULL, 
	transaction_id INTEGER NOT NULL, 
	date_key INTEGER NOT NULL, 
	passenger_sk INTEGER NOT NULL, 
	flight_sk INTEGER NOT NULL, 
	ticket_price NUMERIC(12, 2) NOT NULL, 
	taxes NUMERIC(12, 2) NOT NULL, 
	baggage_fees NUMERIC(12, 2) NOT NULL, 
	total_amount NUMERIC(12, 2) NOT NULL, 
	batch_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	PRIMARY KEY (agency_sale_sk), 
	FOREIGN KEY(date_key) REFERENCES dim_date (date_key), 
	FOREIGN KEY(passenger_sk) REFERENCES dim_passenger (passenger_sk), 
	FOREIGN KEY(flight_sk) REFERENCES dim_flight (flight_sk), 
	FOREIGN KEY(batch_id) REFERENCES ingestion_batches (batch_id)
);


CREATE TABLE fact_corporate_sales (
	corporate_sale_sk SERIAL NOT NULL, 
	transaction_id INTEGER NOT NULL, 
	date_key INTEGER NOT NULL, 
	passenger_sk INTEGER NOT NULL, 
	flight_sk INTEGER NOT NULL, 
	ticket_price NUMERIC(12, 2) NOT NULL, 
	taxes NUMERIC(12, 2) NOT NULL, 
	baggage_fees NUMERIC(12, 2) NOT NULL, 
	total_amount NUMERIC(12, 2) NOT NULL, 
	batch_id INTEGER NOT NULL, 
	source_row INTEGER NOT NULL, 
	PRIMARY KEY (corporate_sale_sk), 
	FOREIGN KEY(date_key) REFERENCES dim_date (date_key), 
	FOREIGN KEY(passenger_sk) REFERENCES dim_passenger (passenger_sk), 
	FOREIGN KEY(flight_sk) REFERENCES dim_flight (flight_sk), 
	FOREIGN KEY(batch_id) REFERENCES ingestion_batches (batch_id)
);

CREATE INDEX ix_dim_airline_is_current ON dim_airline (is_current);
CREATE INDEX ix_dim_airline_airline_key ON dim_airline (airline_key);
CREATE INDEX ix_dim_airport_is_current ON dim_airport (is_current);
CREATE INDEX ix_dim_airport_airport_key ON dim_airport (airport_key);
CREATE INDEX ix_dim_passenger_is_current ON dim_passenger (is_current);
CREATE INDEX ix_dim_passenger_passenger_id ON dim_passenger (passenger_id);
CREATE INDEX ix_mart_passenger_ticket_is_eligible ON mart_passenger_ticket (is_eligible);
CREATE INDEX ix_mart_passenger_ticket_transaction_id ON mart_passenger_ticket (transaction_id);
CREATE INDEX ix_mart_passenger_ticket_passenger_id ON mart_passenger_ticket (passenger_id);
CREATE INDEX ix_mart_passenger_ticket_date_key ON mart_passenger_ticket (date_key);
CREATE INDEX ix_mart_passenger_ticket_passenger_name ON mart_passenger_ticket (passenger_name);
CREATE INDEX ix_mart_passenger_ticket_flight_key ON mart_passenger_ticket (flight_key);
CREATE INDEX ix_mart_passenger_ticket_source_type ON mart_passenger_ticket (source_type);
CREATE INDEX ix_mart_sales_summary_year ON mart_sales_summary (year);
CREATE UNIQUE INDEX ix_dim_flight_flight_key ON dim_flight (flight_key);
CREATE INDEX ix_flight_status_events_event_time ON flight_status_events (event_time);
CREATE INDEX ix_flight_status_events_flight_key ON flight_status_events (flight_key);
CREATE UNIQUE INDEX ix_fact_agency_sales_transaction_id ON fact_agency_sales (transaction_id);
CREATE UNIQUE INDEX ix_fact_corporate_sales_transaction_id ON fact_corporate_sales (transaction_id);
