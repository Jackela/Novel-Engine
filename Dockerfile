# Build stage: install the full workspace (dev tooling included) and compile
# both workspace packages. The SPA dist stays at frontend/dist because the
# server resolves it relative to the workspace root by default. No compile
# toolchain is needed: better-sqlite3 ships prebuilt N-API binaries in its
# npm tarball and installs no build scripts.
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
# No compile toolchain is needed here either: better-sqlite3 loads its
# prebuilt N-API binary straight from the npm tarball. The TS CLI
# (server/dist/apps/cli/main.js) backs up the SQLite store, applies
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
RUN pnpm install --frozen-lockfile --prod --filter novel-engine-server... \
    && rm -rf /root/.cache
COPY --from=build /app/frontend/dist ./frontend/dist
COPY --from=build /app/server/dist ./server/dist
# The startup pipeline locates migrations by the drizzle.config.ts marker and
# applies every SQL file beneath server/drizzle before listening.
COPY server/drizzle.config.ts ./server/drizzle.config.ts
COPY server/drizzle ./server/drizzle
COPY LICENSE README.md ./
# The entrypoint bootstraps the session secret from the persistent volume on
# first boot and then execs the CMD, so signal handling and healthcheck
# behavior are unchanged.
COPY docker/entrypoint.sh ./docker/entrypoint.sh
RUN chmod 0755 ./docker/entrypoint.sh && mkdir -p /app/data
EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["node", "server/dist/apps/cli/main.js", "serve", "--host", "0.0.0.0", "--port", "8000"]
