# syntax=docker/dockerfile:1

FROM python:3.15.2-slim-trixie AS base
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    FLASK_APP=coffer
WORKDIR /app
RUN --mount=from=ghcr.io/astral-sh/uv:0.13.6,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-dev

FROM base AS runtime
RUN useradd --system --no-create-home coffer
COPY pyproject.toml ./
COPY migrations ./migrations
COPY coffer ./coffer
USER coffer
EXPOSE 8000
# Threads, because each request waits on the payment provider.
CMD ["sh", "-c", "alembic upgrade head && exec gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 'coffer:create_app()'"]

# Base plus the dev tools and the tests, for make check and CI.
FROM base AS dev
RUN --mount=from=ghcr.io/astral-sh/uv:0.13.6,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked
COPY . .
