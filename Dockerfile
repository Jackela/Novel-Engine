FROM node:22-bookworm-slim AS frontend
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY frontend/package.json ./frontend/package.json
RUN pnpm install --frozen-lockfile
COPY pyproject.toml ./
COPY frontend ./frontend
RUN pnpm --dir frontend build

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    APP_ENVIRONMENT=production \
    DB_URL=sqlite:///./data/novel-engine.sqlite3
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN pip install --no-cache-dir uv && uv sync --no-dev --frozen
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY scripts ./scripts
COPY --from=frontend /app/frontend/dist ./frontend/dist
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["uv", "run", "novel-engine", "serve", "--host", "0.0.0.0", "--port", "8000"]
