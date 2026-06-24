## ADDED Requirements

### Requirement: Firecrawl Runtime Identity

The application SHALL use `firecrawl-lb` as the primary generic runtime identity.

#### Scenario: Settings load Firecrawl-prefixed environment

- **GIVEN** `FIRECRAWL_LB_DATABASE_URL` is set
- **WHEN** application settings are loaded
- **THEN** the configured database URL SHALL come from `FIRECRAWL_LB_DATABASE_URL`

### Requirement: Firecrawl Persistence

The application SHALL expose SQLAlchemy metadata for Firecrawl account, credential, job, and request-log tables.

#### Scenario: Metadata creates Firecrawl tables

- **GIVEN** a fresh database schema
- **WHEN** SQLAlchemy metadata is created
- **THEN** the Firecrawl account, credential, job, and request-log tables SHALL exist

### Requirement: Firecrawl Account Administration

The application SHALL expose Firecrawl account and credential management APIs under `/v2/admin/firecrawl/accounts`.

#### Scenario: Operator creates and lists Firecrawl accounts

- **GIVEN** an operator submits a Firecrawl account with optional budget and routing limits
- **WHEN** the account is created through `/v2/admin/firecrawl/accounts`
- **THEN** the account SHALL be persisted with `plan_type` defaulting to `unknown`
- **AND** list and detail responses SHALL include nested credential metadata
- **AND** list and detail responses SHALL NOT include plaintext API keys or encrypted key material

#### Scenario: Operator adds a Firecrawl credential

- **GIVEN** an existing Firecrawl account
- **WHEN** an operator adds a credential with plaintext `api_key`
- **THEN** the credential SHALL be stored encrypted
- **AND** the response SHALL include only credential id, name, and status
- **AND** the response SHALL NOT include plaintext API keys or encrypted key material

#### Scenario: Operator updates operational account fields

- **GIVEN** an existing Firecrawl account
- **WHEN** an operator updates status, budget, live usage, RPM, concurrency, or cooldown fields
- **THEN** the persisted Firecrawl account SHALL reflect the updated operational fields

#### Scenario: Operator disables a Firecrawl credential

- **GIVEN** an existing Firecrawl credential
- **WHEN** an operator marks the credential `paused` or `invalid`
- **THEN** the credential SHALL no longer be considered active for proxy routing

#### Scenario: Admin management errors are clean

- **GIVEN** an operator targets a missing account or credential
- **WHEN** the admin request is processed
- **THEN** the API SHALL return 404
- **AND** duplicate account or credential ids SHALL return a clean 409 or 400 response without exposing a raw stacktrace

### Requirement: Firecrawl Dashboard Administration

The application SHALL expose Firecrawl dashboard read APIs under `/v2/admin/firecrawl/jobs`, `/v2/admin/firecrawl/logs`, and `/v2/admin/firecrawl/overview`.

#### Scenario: Operator lists persisted jobs

- **GIVEN** persisted crawl and batch scrape jobs
- **WHEN** an operator requests `/v2/admin/firecrawl/jobs` with optional endpoint, status, limit, and offset filters
- **THEN** the API SHALL return matching job records ordered by `created_at` descending
- **AND** each job SHALL include account, credential, endpoint, upstream id, status, reserved credit, final credit, creation, completion, and last-polled fields

#### Scenario: Operator lists persisted sync request logs

- **GIVEN** persisted scrape, map, and search request logs
- **WHEN** an operator requests `/v2/admin/firecrawl/logs` with optional endpoint, status, limit, and offset filters
- **THEN** the API SHALL return matching request logs ordered by creation time descending
- **AND** each log SHALL include account, credential, endpoint, upstream status, credit, latency, error, and creation fields

#### Scenario: Operator views Firecrawl overview

- **GIVEN** persisted Firecrawl accounts, jobs, and request logs
- **WHEN** an operator requests `/v2/admin/firecrawl/overview`
- **THEN** the API SHALL return total accounts, active accounts, remaining and budget credits, accounts by status, active job count, recent request totals, and endpoint breakdowns

### Requirement: Firecrawl Admin Guard

Firecrawl administrative routes under `/v2/admin/firecrawl/*` SHALL require dashboard/admin authorization through an overrideable FastAPI dependency.

#### Scenario: Unauthenticated admin requests are rejected

- **GIVEN** no dashboard/admin authorization is present
- **WHEN** a client requests a Firecrawl admin endpoint
- **THEN** the API SHALL reject the request
- **AND** Firecrawl public proxy endpoints SHALL NOT require the admin dependency

### Requirement: Firecrawl Team Refresh

The application SHALL refresh Firecrawl account credit usage and queue status from the active credential for each account.

#### Scenario: Credit usage and queue status refresh persist live fields

- **GIVEN** a Firecrawl account has an active credential
- **WHEN** the refresh pass calls `/v2/team/credit-usage` and `/v2/team/queue-status`
- **THEN** the upstream API key SHALL be the active credential key
- **AND** `remaining_credits_live`, `plan_credits_live`, billing dates, queue active jobs, queue max concurrency, and refresh timestamps SHALL be persisted
- **AND** common top-level or nested `data` response shapes SHALL be accepted
- **AND** API keys SHALL NOT be persisted in refresh error messages or returned by admin responses

### Requirement: Firecrawl V2 Proxy

The application SHALL proxy Firecrawl `/v2/scrape`, `/v2/map`, `/v2/search`, `/v2/crawl`, and `/v2/batch/scrape` requests through persisted Firecrawl credentials.

#### Scenario: Successful scrape is forwarded and logged

- **GIVEN** an active Firecrawl account and encrypted active credential
- **WHEN** a client posts to `/v2/scrape`
- **THEN** the proxy SHALL forward the payload upstream using the credential as Authorization
- **AND** the proxy SHALL return the upstream status and body
- **AND** the proxy SHALL record a Firecrawl request log
- **AND** the proxy SHALL decrement the local remaining-credit estimate

#### Scenario: Upstream rate limit cools account down

- **GIVEN** an active Firecrawl account and encrypted active credential
- **WHEN** upstream returns 429 with `Retry-After`
- **THEN** the account SHALL be marked `rate_limited`
- **AND** `cooldown_until` SHALL be set from `Retry-After`

#### Scenario: Submitted jobs preserve account ownership

- **GIVEN** a client submits a crawl or batch scrape job
- **WHEN** upstream returns a job id
- **THEN** the proxy SHALL persist the job with the selected account, credential, endpoint, upstream job id, and estimated reserved credits
- **AND** later status or cancel requests for that job SHALL use the original credential
- **AND** the proxy SHALL NOT re-select a different account for existing job operations

#### Scenario: Terminal job status settles credits once

- **GIVEN** a persisted crawl or batch scrape job has not been settled
- **WHEN** a status response contains a terminal status and `creditsUsed`
- **THEN** the proxy SHALL decrement the owning account's live remaining credits once
- **AND** repeated status polls SHALL NOT decrement credits again

### Requirement: Firecrawl Runtime Surface

The application SHALL expose Firecrawl `/v2/*` proxy routes plus health and admin-support routes.

### Requirement: Firecrawl Deployment Artifacts

Active deployment and release artifacts SHALL use the `firecrawl-lb` runtime identity, `FIRECRAWL_LB_` environment prefix, port `2465`, and `/var/lib/firecrawl-lb` container data path.

#### Scenario: Deployment artifacts use Firecrawl identity

- **GIVEN** an operator uses Docker, Compose, Helm, or release automation
- **WHEN** the artifact starts, publishes, or installs firecrawl-lb
- **THEN** the exposed HTTP service SHALL use port `2465`
- **AND** runtime data SHALL be mounted under `/var/lib/firecrawl-lb`
- **AND** chart, image, release, and workflow references SHALL use firecrawl-lb names
- **AND** legacy proxy/auth/session deployment settings SHALL NOT be required
