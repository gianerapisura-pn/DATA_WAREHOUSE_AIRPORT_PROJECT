# User Guide

## Dashboard

The dashboard shows loaded ticket count, total sales, disruption counts, eligible records, monthly sales hierarchy, and recent ingestion batches.

## Upload page

Select the matching dataset type before choosing a CSV. The page returns received, loaded, rejected, and repaired counts. Dimensions should be loaded before facts.

Recommended order for a fresh database:

1. Airlines
2. Airports
3. Passengers
4. Flights
5. Corporate sales
6. Travel-agency sales
7. Passenger updates
8. Flight-status events

The bootstrap script already follows this order.

## Check-in lookup

Search by:

- passenger ID;
- passenger name;
- flight number;
- airline name;
- origin or destination airport code;
- transaction ID.

The result is formatted as a ticket and includes the latest flight status and eligibility decision.

## Data quality

The data-quality page shows every ingestion batch and the latest rejected rows. The source row number allows the original record to be located.

## SCD history

Enter a passenger ID to view old and current versions. `P1001` and `P1002` have demo changes after the default bootstrap.
