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
