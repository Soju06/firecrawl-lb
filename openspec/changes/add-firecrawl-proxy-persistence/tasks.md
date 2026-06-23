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

## 7. Frontend dashboard cutover

- [x] Specify Firecrawl dashboard job/log/overview read APIs.
- [x] Add RED tests for Firecrawl admin job list, request-log list, and overview aggregation.
- [x] Implement Firecrawl admin job, request-log, and overview endpoints.
- [x] Replace old dashboard routes with Firecrawl overview, accounts, jobs, logs, and settings pages.
- [x] Run frontend typecheck and build.
- [x] Run targeted backend pytest, ruff, ty, and OpenSpec validation.

## 8. Codex/OpenAI residue cleanup

- [x] Delete old backend Codex/OpenAI/OAuth/API-key/dashboard/usage/request-log/quota/sticky-session/conversation/limit-warmup modules.
- [x] Remove deleted backend router, scheduler, cache, bridge, ring-membership, and usage-registry wiring from `app/main.py`.
- [x] Delete old backend tests that import deleted modules while keeping Firecrawl tests.
- [x] Delete old frontend Codex dashboard/accounts/API/firewall/sticky/quota/conversation feature areas and integration tests.
- [x] Trim frontend mocks, auth branding, shared status/runtime/settings references, and old hook/component imports.
- [x] Run backend and frontend verification for the cleanup slice.

## 9. Deployment system parity

- [x] Rename Docker, Compose, Helm, release, and GitHub automation artifacts to firecrawl-lb identity.
- [x] Move the Helm chart to `deploy/helm/firecrawl-lb` and update chart helpers, labels, dashboard metadata, and release-managed paths.
- [x] Replace deployment env vars with `FIRECRAWL_LB_*`, port `2465`, and `/var/lib/firecrawl-lb` runtime paths.
- [x] Remove Codex/OpenAI/OAuth/session-bridge deployment values and examples from active deployment artifacts.
- [x] Preserve generic database, migration, metrics, tracing, ingress, service, HPA, PDB, NetworkPolicy, and release workflows.
- [x] Record deployment verification at `/tmp/firecrawl-deploy-system-verification.md`.
