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

### Requirement: Firecrawl V2 Proxy

The application SHALL proxy Firecrawl `/v2/scrape`, `/v2/map`, and `/v2/search` requests through persisted Firecrawl credentials.

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
