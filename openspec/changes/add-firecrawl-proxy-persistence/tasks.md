## 1. Runtime identity

- [x] Rename primary project/config/runtime identity to firecrawl-lb.
- [x] Update test harness to use `FIRECRAWL_LB_*` settings.

## 2. Persistence

- [x] Add Firecrawl account, credential, job, and request-log models to SQLAlchemy metadata.
- [x] Cover metadata table creation in tests.

## 3. Proxy

- [x] Add an async Firecrawl upstream client.
- [x] Add repository/service/router for `/v2/scrape`, `/v2/map`, and `/v2/search`.
- [x] Record request logs and state transitions for success, 401, 402, and 429.
- [x] Cover proxy success and rate-limit handling with fake upstream clients.

## 4. Verification

- [x] Run targeted pytest.
- [x] Run ruff on changed app/test paths.
- [x] Run ty on changed app/test paths.

## 5. Account administration

- [x] Specify Firecrawl account and credential admin management behavior.
- [x] Add endpoint-level RED tests for account create/list/detail, credential add/update, not-found, duplicate, and secret redaction behavior.
- [x] Implement Firecrawl account and credential admin API under `/v2/admin/firecrawl/accounts`.
- [x] Persist account RPM limits and preserve existing proxy routing behavior.
- [x] Run targeted pytest.
- [x] Run ruff on changed app/test paths.
- [x] Run ty on changed app/test paths.
- [x] Run strict OpenSpec validation.

## 6. Cutover slice

- [x] Specify Firecrawl team refresh, admin guard, job ownership/settlement, and old-route removal behavior.
- [x] Add RED tests for team credit/queue refresh persistence.
- [x] Add RED tests for Firecrawl admin auth dependency override and public proxy openness.
- [x] Add RED tests for `/v2/crawl` and `/v2/batch/scrape` submit/status/cancel ownership and one-time settlement.
- [x] Add RED tests that old OpenAI/OAuth runtime routes are absent.
- [x] Implement refresh client/service/scheduler wiring without real network calls in tests.
- [x] Implement job proxy routes and original-account settlement.
- [x] Remove old OpenAI/OAuth/WebSocket routers from app wiring while keeping shared app infrastructure bootable.
- [x] Rewrite README for firecrawl-lb operation.
- [x] Run targeted pytest.
- [x] Run ruff on changed app/test paths.
- [x] Run ty on changed app/test paths.
- [x] Run strict OpenSpec validation.
