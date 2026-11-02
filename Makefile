.PHONY: check test down

check:
	docker compose run --rm --build dev scripts/check.sh

test:
	docker compose run --rm --build dev pytest

down:
	docker compose --profile dev down --volumes
