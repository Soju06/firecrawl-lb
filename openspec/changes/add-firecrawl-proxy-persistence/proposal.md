# Change: Add Firecrawl proxy persistence

## Why

The Firecrawl cutover needs the runtime identity to move from the source scaffold to firecrawl-lb and an MVP persistence/proxy path for Firecrawl requests.

## What Changes

- Rename generic application identity/config defaults to firecrawl-lb names and `FIRECRAWL_LB_` settings.
- Add persistence records for Firecrawl accounts, credentials, jobs, and request logs.
- Add a minimal Firecrawl upstream client and proxy routes for `/v2/scrape`, `/v2/map`, and `/v2/search`.
- Record request outcomes and update account/credential state on success, auth failure, credit exhaustion, and rate limiting.

## Impact

- Adds Firecrawl-specific DB tables and proxy routes.
- Keeps existing legacy modules removed after Firecrawl cutover.
- Tests use fake upstream clients and do not require real Firecrawl credentials.
