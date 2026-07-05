# =============================================================================
# COBOL/JCL Migration Harness — convenience targets
# =============================================================================
# All targets assume `.env` exists at repo root (copy from .env.example).
# Nothing in this Makefile hardcodes config; docker-compose.yml and the
# scripts it calls read from .env themselves.

.PHONY: up down restart logs init-db test test-backend test-frontend clean

## Bring up the full local stack in the background.
up:
	docker-compose up -d

## Tear down the full local stack (containers only; named volumes persist).
down:
	docker-compose down

## Restart the full stack.
restart: down up

## Tail logs for all services.
logs:
	docker-compose logs -f

## Create the 7 CouchDB databases + Mango indexes + audit_log validate_doc_update
## design doc. Requires couchdb to be up (`make up` or `docker-compose up couchdb -d`
## first). Phase 2 adds the real script at this path.
init-db:
	python infra/couchdb/init_databases.py

## Run the full test suite: pytest across every backend package with tests,
## then npm test across every frontend package with tests. Most packages are
## still stubs this pass and will no-op or report "no tests collected" until
## later phases add real code — that is expected, not a failure.
test: test-backend test-frontend

## Python/pytest suite across every backend package.
test-backend:
	pytest mcp_gateway/tests
	pytest agents/tests
	pytest orchestrator/tests
	pytest backend/shared/tests
	pytest backend/source_mgmt_service/tests
	pytest backend/job_pipeline_control_service/tests
	pytest backend/recommendation_service/tests
	pytest backend/epic_story_service/tests
	pytest backend/ingestion_bff/tests
	pytest backend/review_bff/tests
	pytest backend/editor_admin_bff/tests

## npm test across every frontend package.
test-frontend:
	npm test --prefix frontend/shared-deps
	npm test --prefix frontend/design-system
	npm test --prefix frontend/shell
	npm test --prefix frontend/upload-mfe
	npm test --prefix frontend/review-mfe
	npm test --prefix frontend/editor-mfe
	npm test --prefix frontend/admin-mfe

## Remove local Python/Node build & cache artifacts (does not touch .env or
## docker volumes).
clean:
	find . -type d -name "__pycache__" -not -path "./node_modules/*" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "node_modules" -prune -o -type d -name "dist" -exec rm -rf {} +
