## ADDED Requirements

### Requirement: PR-Gated Beta Releases

Beta release metadata SHALL be merged and published only from canonical firecrawl-lb beta release PRs with recorded release-candidate validation evidence.

#### Scenario: Beta PR requires canonical branch and validation evidence

- **GIVEN** release-managed version files advance to a beta version
- **WHEN** CI evaluates the pull request
- **THEN** the PR head branch SHALL be `release/beta-<version>`
- **AND** the PR head repository SHALL be the canonical repository
- **AND** the PR body SHALL include a release-candidate validation section naming the exact PR head SHA
- **AND** the required backend, frontend, wheel, and container validation items SHALL be checked
- **AND** either live upstream/account smoke or an explicit not-required item SHALL be checked

#### Scenario: Beta publish requires validated candidate tree

- **GIVEN** a canonical beta release PR is merged
- **WHEN** the beta publish workflow runs
- **THEN** the publish guard SHALL verify validation evidence for the merged PR head SHA
- **AND** the published merge commit tree SHALL match the validated PR head commit tree
- **AND** install snippets SHALL use the `firecrawl-lb` package, command, image, and Helm chart names

### Requirement: Complete Stable Release Promotions

Stable release metadata SHALL be promoted only by release-please and SHALL advance all release-managed version fields together.

#### Scenario: Stable release promotion uses release-please branch

- **GIVEN** release-managed version files advance to a stable version
- **WHEN** CI evaluates the pull request
- **THEN** the PR head branch SHALL be `release-please--branches--main`
- **AND** the PR head repository SHALL be the canonical repository
- **AND** all release-managed version fields SHALL agree on the promoted stable version
- **AND** all release-managed version fields SHALL have changed from the base ref together
