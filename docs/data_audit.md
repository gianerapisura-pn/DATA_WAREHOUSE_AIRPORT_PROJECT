# Data Audit

The raw files were profiled before warehouse loading. Repairs are logged in `data/rejected/*_repairs.csv`; rejected rows are stored beside them.

| Dataset | Received | Cleaned | Rejected | Repairs logged |
|---|---:|---:|---:|---:|
| airlines | 39 | 39 | 0 | 14 |
| airports | 216 | 221 | 0 | 106 |
| passengers | 2831 | 2822 | 9 | 205 |
| flights | 390 | 390 | 0 | 1 |
| corporate_sales | 100 | 100 | 0 | 101 |
| travel_agency_sales | 301 | 298 | 3 | 302 |
| passenger_updates | 2 | 2 | 0 | 0 |
| flight_status_events | 12 | 12 | 0 | 0 |

## Main decisions

- `corporate_sales.sql` duplicates the corporate CSV record-for-record and is retained only as a legacy reference.
- The original `DimDate.sql` uses SQL Server syntax. The project generates a PostgreSQL/SQLite-compatible date dimension instead.
- Airport rows were trimmed, country names standardized, duplicate KEF and MDW records collapsed, and seven airport codes required by the flight file were added.
- Flight `AF023` used `JK`; it was corrected to `JFK`.
- Passenger marker rows and a repeated header were rejected. Corrupted passenger keys and one malformed email were repaired.
- Sales passenger IDs were mapped to the passenger dimension. The professor-confirmed P90001/P90002 mappings resolve to P1001/P1002.
- Travel transaction IDs `4AN`, `4GW`, and `4G4` were restored from sequence. One exact duplicate was rejected. The missing flight on transaction 40011 was restored as LH400.
- Two travel rows with no passenger ID remain rejected because no reliable passenger identity can be inferred.
- Corporate transaction 10092 had an incorrect total. The total was recalculated from its three components.
- Flight-status and passenger-update files are clearly labeled demo inputs because the raw sources did not contain disruption events or repeated business-key updates.
