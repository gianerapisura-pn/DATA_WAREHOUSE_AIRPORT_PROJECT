# Known Limitations

- The source flight file contains route and aircraft information but no scheduled departure, actual departure, flight occurrence date, or operational status.
- Demo status events are therefore keyed by `FlightKey`. A production design should use a separate flight-occurrence key containing flight number and departure date/time.
- The sales date is treated as the available transaction date; it is not claimed to be the actual departure date.
- The eligibility threshold is configurable and defaults to 180 minutes because the exact threshold in the classroom photo was unclear.
- The website is an academic prototype and has no user authentication. Database credentials remain server-side.
- Kafka is included as a demonstrable event path. The application can also be used without Kafka by uploading the event CSV or calling the API.
- Seven airport master records are added because flights reference their codes but the airport file omits them. These additions are logged as repairs.
- Two travel sales with missing passenger IDs are rejected rather than assigned to guessed passengers.
