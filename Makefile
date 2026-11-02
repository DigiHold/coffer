.PHONY: up demo check test psql down

seed = docker compose exec -T db psql --quiet -v ON_ERROR_STOP=1 --username=coffer --dbname=coffer < db/seed.sql

up:
	docker compose up --build --detach --wait db api
	$(seed)

demo:
	$(seed)
	scripts/demo.sh

check:
	docker compose run --rm --build dev scripts/check.sh

test:
	docker compose run --rm --build dev pytest

psql:
	docker compose exec db psql --username=coffer --dbname=coffer

down:
	docker compose --profile dev down --volumes
