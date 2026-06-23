# Change: Add Firecrawl proxy persistence

## Why

The Firecrawl cutover needs the runtime identity to move from codex-lb to firecrawl-lb while the old Codex modules remain bootable, and it needs an MVP persistence/proxy path for Firecrawl requests.

## What Changes

- Rename generic application identity/config defaults to firecrawl-lb names and `FIRECRAWL_LB_` settings.
- Add persistence records for Firecrawl accounts, credentials, jobs, and request logs.
- Add a minimal Firecrawl upstream client and proxy routes for `/v2/scrape`, `/v2/map`, and `/v2/search`.
- Record request outcomes and update account/credential state on success, auth failure, credit exhaustion, and rate limiting.

## Impact

- Adds Firecrawl-specific DB tables and proxy routes.
- Keeps existing Codex/OpenAI modules present for boot compatibility.
- Tests use fake upstream clients and do not require real Firecrawl credentials.
