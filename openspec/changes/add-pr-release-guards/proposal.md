# Change: Add PR release guards

## Why

firecrawl-lb has PR-driven beta release automation, but the release path needs the stricter PR guard behavior from the source gateway before beta and stable release metadata can publish.

## What Changes

- Require beta release PRs to come from the canonical `release/beta-*` branch in the canonical repository.
- Require beta release PR bodies to record release-candidate validation evidence for the exact candidate SHA.
- Require the beta publish workflow to verify validation evidence and confirm the published merge tree matches the validated candidate.
- Require stable release promotions to come from the release-please branch and advance all release-managed version files together.

## Impact

- Adds release guard scripts, CI hooks, publish workflow gating, and focused tests.
- Keeps release artifact names and install snippets aligned to firecrawl-lb.
