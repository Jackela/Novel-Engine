# Novel Studio

Novel Studio `0.3.0` is a self-hosted single-author novel writing IDE. SQLite is
the content authority and Markdown is the document syntax.

## Install

```bash
uv sync --extra dev --extra test
corepack pnpm install --frozen-lockfile
corepack pnpm --dir frontend build
```

Docker installation:

```bash
docker compose up --build
```

## Start

```bash
uv run novel-engine serve --reload
```

Open `http://127.0.0.1:8000`.

## Product Specification

[`openspec/specs/novel-studio/spec.md`](openspec/specs/novel-studio/spec.md) is
the only product definition. Validate it with:

```bash
corepack pnpm spec:validate
```
