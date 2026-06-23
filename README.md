# firecrawl-lb

Firecrawl account load balancer and persistence proxy.

`firecrawl-lb` fronts selected Firecrawl `/v2` APIs, routes requests across configured Firecrawl team credentials, records request/job state locally, and keeps live account usage fields refreshed for operators.

## What It Proxies

Public proxy endpoints:

- `POST /v2/scrape`
- `POST /v2/map`
- `POST /v2/search`
- `POST /v2/crawl`
- `GET /v2/crawl/{job_id}`
- `DELETE /v2/crawl/{job_id}`
- `POST /v2/batch/scrape`
- `GET /v2/batch/scrape/{job_id}`
- `DELETE /v2/batch/scrape/{job_id}`

Admin endpoints:

- `GET /v2/admin/firecrawl/accounts`
- `POST /v2/admin/firecrawl/accounts`
- `GET /v2/admin/firecrawl/accounts/{account_id}`
- `PATCH /v2/admin/firecrawl/accounts/{account_id}`
- `POST /v2/admin/firecrawl/accounts/{account_id}/credentials`
- `PATCH /v2/admin/firecrawl/accounts/{account_id}/credentials/{credential_id}`

Health endpoints remain available through the existing app health module.

## Quick Start

```bash
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 2465
```

The default data directory is `~/.firecrawl-lb` outside containers and `/var/lib/firecrawl-lb` in containers. The default database is SQLite at that data directory.

Useful environment variables:

```bash
FIRECRAWL_LB_DATABASE_URL=sqlite+aiosqlite:///./firecrawl-lb.db
FIRECRAWL_LB_DATA_DIR=~/.firecrawl-lb
FIRECRAWL_LB_ENCRYPTION_KEY_FILE=~/.firecrawl-lb/encryption.key
FIRECRAWL_LB_DATABASE_MIGRATE_ON_STARTUP=true
FIRECRAWL_LB_METRICS_ENABLED=false
```

## Configure Accounts

Create an account:

```bash
curl -X POST http://127.0.0.1:2465/v2/admin/firecrawl/accounts \
  -H 'content-type: application/json' \
  -d '{
    "id": "team-a",
    "team_label": "Team A",
    "plan_type": "standard",
    "monthly_budget_credits": 100000,
    "remaining_credits_live": 100000,
    "plan_credits_live": 100000,
    "rpm_limit": 500,
    "max_concurrency": 50
  }'
```

Add a credential:

```bash
curl -X POST http://127.0.0.1:2465/v2/admin/firecrawl/accounts/team-a/credentials \
  -H 'content-type: application/json' \
  -d '{
    "id": "team-a-primary",
    "name": "primary",
    "api_key": "fc-your-firecrawl-key"
  }'
```

Admin responses redact API keys and encrypted key material. Credentials are stored encrypted with the configured encryption key file.

## Proxy Behavior

Synchronous endpoints select an active account and credential, forward the request to Firecrawl, return the upstream status/body, and write a local request log. Successful synchronous responses decrement `remaining_credits_live` using Firecrawl `creditsUsed` when present, otherwise the local estimator.

Job submit endpoints (`/v2/crawl`, `/v2/batch/scrape`) persist a `firecrawl_jobs` row with the selected `account_id`, `credential_id`, endpoint, upstream job id, and reserved-credit estimate. Status and cancel calls always use the original credential for that job; they do not re-run account selection.

When a status response is terminal and includes `creditsUsed`, `firecrawl-lb` settles the job once and decrements the owning account once. Repeated status polls do not double-charge the local live balance.

## Refresh Behavior

The refresh service calls each account's active credential against:

- `GET /v2/team/credit-usage`
- `GET /v2/team/queue-status`

It accepts common top-level and nested `data` response shapes, then persists:

- `remaining_credits_live`
- `plan_credits_live`
- `billing_period_start`
- `billing_period_end`
- `queue_active_jobs`
- `queue_max_concurrency`
- `last_usage_refresh_at`
- `last_queue_refresh_at`
- `last_refresh_error_at`
- `last_refresh_error_message`

The scheduler shell is disabled by default in this cutover slice. The one-pass refresh service is covered by tests and can be wired to an operator-controlled interval when the rollout policy is finalized.

## Limitations

- This slice focuses runtime Firecrawl proxy/admin behavior and top-level docs.
- No tests make real Firecrawl network calls; upstream behavior is exercised with fake clients.
- Dashboard/frontend cleanup is outside this MVP slice unless needed for backend bootability.

## Verification

Common local checks:

```bash
uv run pytest tests/unit/test_firecrawl_routing_usage.py tests/unit/test_firecrawl_proxy_persistence.py tests/unit/test_firecrawl_admin_api.py tests/unit/test_firecrawl_cutover.py -q
uvx ruff check app/modules/firecrawl app/core/config/settings.py app/db/models.py app/main.py tests/unit/test_firecrawl_*.py
uv run ty check app/modules/firecrawl app/core/config/settings.py tests/unit/test_firecrawl_routing_usage.py tests/unit/test_firecrawl_proxy_persistence.py tests/unit/test_firecrawl_admin_api.py tests/unit/test_firecrawl_cutover.py
openspec validate add-firecrawl-proxy-persistence --strict
```
