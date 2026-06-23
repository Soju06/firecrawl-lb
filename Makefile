PYTEST_ARGS := -q -ra -o faulthandler_timeout=300 -o faulthandler_exit_on_timeout=true --timeout=180 --timeout-method=thread --durations=20
POSTGRES_TEST_DATABASE_URL ?= postgresql+asyncpg://firecrawl_lb:firecrawl_lb@127.0.0.1:5432/firecrawl_lb
SHELL := /bin/bash

.PHONY: help
help:
	@printf '%s\n' \
	  'Common targets:' \
	  '  make lint                    ruff check + format check' \
	  '  make typecheck               ty check' \
	  '  make frontend-test           vitest, same as CI' \
	  '  make test-unit               unit pytest slice' \
	  '  make test-integration        integration pytest slice' \
	  '  make package                 build and verify sdist/wheel' \
	  '  make ci-fast                 lint/type/frontend/unit/package' \
	  '  make ci                      full local CI gate'

.PHONY: frontend-install frontend-lint frontend-typecheck frontend-test frontend-build
frontend-install:
	cd frontend && bun install --frozen-lockfile

frontend-lint: frontend-install
	cd frontend && bun run lint

frontend-typecheck: frontend-install
	cd frontend && bun run typecheck

frontend-test: frontend-install
	cd frontend && bun run test

frontend-build: frontend-install
	cd frontend && bun run build

.PHONY: lint typecheck
lint:
	uvx ruff check .
	uvx ruff format --check .

typecheck:
	uv sync --dev --frozen
	uv run ty check

.PHONY: test-unit test-integration test-e2e test-postgres
test-unit: frontend-build
	uv sync --dev --frozen
	PYTHONFAULTHANDLER=1 uv run pytest $(PYTEST_ARGS) tests/unit

test-integration: frontend-build
	uv sync --dev --frozen
	PYTHONFAULTHANDLER=1 uv run pytest $(PYTEST_ARGS) tests/integration

test-integration-core: test-integration

test-integration-bridge: test-integration

test-e2e: frontend-build
	uv sync --dev --frozen
	@if find tests/e2e -name 'test_*.py' -print -quit 2>/dev/null | grep -q .; then \
	  PYTHONFAULTHANDLER=1 uv run pytest $(PYTEST_ARGS) tests/e2e; \
	else \
	  echo "No e2e tests present; skipping"; \
	fi

test-postgres:
	uv sync --dev --frozen
	FIRECRAWL_LB_TEST_DATABASE_URL="$${FIRECRAWL_LB_TEST_DATABASE_URL:-$(POSTGRES_TEST_DATABASE_URL)}" \
	  PYTHONFAULTHANDLER=1 \
	  uv run pytest $(PYTEST_ARGS) tests/integration

.PHONY: migration-check migration-check-postgres
migration-check:
	uv sync --dev --frozen
	TMP_DB="$$(mktemp -u /tmp/firecrawl-lb-ci-migrate-XXXXXX.db)"; \
	DB_URL="sqlite+aiosqlite:///$${TMP_DB}"; \
	trap 'rm -f "$${TMP_DB}"' EXIT; \
	uv run firecrawl-lb-db --db-url "$${DB_URL}" upgrade head; \
	uv run firecrawl-lb-db --db-url "$${DB_URL}" check

migration-check-postgres:
	uv sync --dev --frozen
	uv run firecrawl-lb-db --db-url "$(POSTGRES_TEST_DATABASE_URL)" upgrade head
	uv run firecrawl-lb-db --db-url "$(POSTGRES_TEST_DATABASE_URL)" check

.PHONY: package
package: frontend-build
	uv sync --frozen --no-dev
	uv run python -c "import app; import app.main; print('import ok')"
	rm -rf build dist *.egg-info
	uvx --from build==1.3.0 python -m build
	python scripts/verify-wheel-assets.py

.PHONY: docker
docker:
	docker build -t firecrawl-lb:ci .
	trivy image --format table --exit-code 1 --severity CRITICAL --ignore-unfixed firecrawl-lb:ci

.PHONY: helm-deps helm-lint helm-template helm-kubeconform
helm-deps:
	helm dependency build deploy/helm/firecrawl-lb/

helm-lint: helm-deps
	helm lint --strict deploy/helm/firecrawl-lb/ --set postgresql.auth.password=test-password
	helm lint --strict deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-dev.yaml --set postgresql.auth.password=test-password
	helm lint --strict deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-bundled.yaml --set postgresql.auth.password=test-password
	helm lint --strict deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-external-db.yaml --set externalDatabase.url=postgresql+asyncpg://test:test@localhost/test
	helm lint --strict deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-external-secrets.yaml --set externalSecrets.secretStoreRef.name=test-store
	helm lint --strict deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-staging.yaml --set externalDatabase.url=postgresql+asyncpg://test:test@localhost/test
	helm lint --strict deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-prod.yaml --set externalSecrets.secretStoreRef.name=test-store

helm-template:
	helm template firecrawl-lb deploy/helm/firecrawl-lb/ --set postgresql.auth.password=test-password > /dev/null
	helm template firecrawl-lb deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-dev.yaml --set postgresql.auth.password=test-password > /dev/null
	helm template firecrawl-lb deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-bundled.yaml --set postgresql.auth.password=test-password > /dev/null
	helm template firecrawl-lb deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-external-db.yaml --set externalDatabase.url=postgresql+asyncpg://test:test@localhost/test > /dev/null
	helm template firecrawl-lb deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-external-secrets.yaml --set externalSecrets.secretStoreRef.name=test-store > /dev/null
	helm template firecrawl-lb deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-staging.yaml --set externalDatabase.url=postgresql+asyncpg://test:test@localhost/test > /dev/null
	helm template firecrawl-lb deploy/helm/firecrawl-lb/ -f deploy/helm/firecrawl-lb/values-prod.yaml --set externalSecrets.secretStoreRef.name=test-store > /dev/null

helm-kubeconform:
	set -e -o pipefail; \
	for version in 1.32.0 1.35.0; do \
	  helm template firecrawl-lb deploy/helm/firecrawl-lb/ \
	    -f deploy/helm/firecrawl-lb/values-prod.yaml \
	    --set externalSecrets.secretStoreRef.name=test \
	    --set externalSecrets.secretStoreRef.kind=SecretStore \
	    --set gatewayApi.enabled=true \
	    --set "gatewayApi.parentRefs[0].name=test-gw" \
	    --set "gatewayApi.hostnames[0]=test.example.com" \
	    | kubeconform \
	      -strict \
	      -kubernetes-version "$${version}" \
	      -schema-location default \
	      -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
	      -summary; \
	done

.PHONY: helm-check helm-smoke-kind
helm-check: helm-lint helm-template helm-kubeconform

helm-smoke-kind: helm-lint helm-template
	@echo "kind smoke installer was removed with legacy deployment scripts; helm-check is the smoke gate"

.PHONY: ci-fast ci
ci-fast: lint typecheck frontend-test test-unit package

ci: frontend-lint frontend-typecheck frontend-test frontend-build lint typecheck \
	test-unit test-integration test-e2e migration-check package docker helm-check
