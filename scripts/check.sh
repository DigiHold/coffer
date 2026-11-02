#!/bin/sh
# Every quality gate, run inside the dev image by make check and by CI.
set -eux

ruff check .
ruff format --check .
mypy .
# Both directions of every migration, on the test database.
alembic downgrade base
alembic upgrade head
pytest --cov
