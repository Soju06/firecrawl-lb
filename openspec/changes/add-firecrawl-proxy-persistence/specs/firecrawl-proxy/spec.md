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
