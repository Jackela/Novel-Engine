# Build stage: install the full workspace (dev tooling included) and compile
# both workspace packages. The SPA dist stays at frontend/dist because the
# server resolves it relative to the workspace root by default.
FROM node:24-bookworm-slim AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY frontend/package.json ./frontend/package.json
COPY server/package.json ./server/package.json
RUN pnpm install --frozen-lockfile
COPY frontend ./frontend
COPY server ./server
RUN pnpm --dir frontend build && pnpm --dir server build

# Runtime stage: production dependencies only, plus the built artifacts.
# The TS CLI (server/dist/apps/cli/main.js) backs up the SQLite store, applies
# migrations, and serves the API and the SPA from one process.
FROM node:24-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    APP_ENVIRONMENT=production \
    DB_URL=sqlite:///./data/novel-engine.sqlite3
RUN corepack enable
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY frontend/package.json ./frontend/package.json
COPY server/package.json ./server/package.json
RUN pnpm install --frozen-lockfile --prod
COPY --from=build /app/frontend/dist ./frontend/dist
COPY --from=build /app/server/dist ./server/dist
COPY LICENSE README.md ./
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["node", "server/dist/apps/cli/main.js", "serve", "--host", "0.0.0.0", "--port", "8000"]
