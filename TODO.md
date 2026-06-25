# TODO — EventZone upgrades

## Phase 1 (Safety & correctness)
- [ ] Add concurrency-safe ticket reservation (transaction + row locking or atomic update strategy)
- [ ] Add booking expiration for `pending` and auto-release of inventory
- [ ] Make MTN MoMo pending state persistent (DB table instead of in-memory dict)
- [ ] Add payment idempotency / duplicate confirmation protection

## Phase 2 (Ticketing & check-in)
- [ ] Add per-ticket serials (for `ticket_quantity`) and embed serials in generated PDF
- [ ] Add ticket verification/check-in endpoint and persistence (mark used)
- [ ] Add QR payload support (even if simulated first)

## Phase 3 (Admin consistency)
- [ ] Ensure admin booking status updates keep `Event.tickets_sold` consistent
- [ ] Add audit fields for status changes (who/when)

## Phase 4 (UX & platform hardening)
- [ ] Add sold-out / remaining tickets messaging in event responses
- [ ] Restrict CORS to allowed origins (remove wildcard in production)
- [ ] Add basic rate limiting on auth + payment confirm

