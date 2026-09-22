FROM ghcr.io/astral-sh/uv:0.11.6 AS uv

FROM python:3.13.12-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable --python /usr/local/bin/python

FROM python:3.13.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH" UVICORN_HOST=0.0.0.0 UVICORN_PORT=8080
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
COPY --from=builder /app/.venv /app/.venv
COPY app ./app
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini ./
USER 10001:10001
EXPOSE ${UVICORN_PORT}
CMD ["uvicorn", "app.main:create_app", "--factory", "--no-proxy-headers", "--no-access-log"]
