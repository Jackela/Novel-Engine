# Demo workspace: "The Cartographer of Lost Hours"

A realistic legacy writing workspace you can import into a running Novel Engine
instance to give a two-minute product demo: a pitch-ready novel opening with a
title, a premise, and four finished chapters.

Layout (exactly what the import reader accepts):

```text
story.yaml                        # title / premise (single-line scalars)
manuscript/chapters/chapter-001.md
manuscript/chapters/chapter-002.md
manuscript/chapters/chapter-003.md
manuscript/chapters/chapter-004.md
```

Import creates a project titled *The Cartographer of Lost Hours* whose chapters
become documents named `Chapter 1`..`Chapter 4` inside a default volume.

## Docker (recommended)

From the repository root, with the published image or a local build:

```sh
# 1. Start the stack (port 8000, mock AI provider by default — no API keys).
docker compose up -d
docker compose ps   # wait until novel-engine is healthy

# 2. In a browser, open http://localhost:8000 and complete the first-run
#    owner setup (username + password). The CLI import runs as that owner.

# 3. Copy the workspace into the container's data volume and import it.
docker compose exec novel-engine mkdir -p /app/data/imports
docker compose cp examples/demo-workspace/. novel-engine:/app/data/imports/demo-workspace
docker compose exec novel-engine node server/dist/apps/cli/main.js \
  import --source /app/data/imports/demo-workspace
```

The import prints a JSON summary (`project_id`, `created`, `chapter_count`)
and is idempotent: running it again reports the same project with
`"created": false` instead of duplicating it. Refresh the Projects page and the
imported project is there.

If the instance has several owners, add `--owner <username>` to the import
command.

## Local development

Two terminals from the repository root:

```sh
# Terminal 1: build the SPA into frontend/dist so the server can serve it.
pnpm --dir frontend build
pnpm --dir server cli serve          # builds the server, serves on :8000

# Terminal 2: import the demo workspace (or use another terminal for step 3
# of the Docker flow instead — same result).
pnpm --dir server cli import --source examples/demo-workspace
```

Data lands in `data/novel-engine.sqlite3` under the workspace root; delete that
directory for a clean slate between demos.

Prefer the Vite dev loop? Run `pnpm --dir frontend dev` (port 5173, `/api`
proxied to :8000) instead of building the SPA.

## The zero-key demo flow

Docker sets `LLM_PROVIDER: mock` by default (local dev defaults to the mock
provider as well), so every step below works without any provider credentials:

1. Open the imported project. All four chapters are in the manuscript.
2. Select a chapter, open the **Copilot** tab, type an instruction such as
   "Continue with the storm arriving early" and press **Continue** — the mock
   provider streams a deterministic draft you can preview and **Accept**.
3. Open the **Export** tab and download a Markdown/DOCX/EPUB export rendered
   from the accepted revisions.

That is the full loop — import, generate, accept, export — with no keys and no
network dependencies, suitable for a live pitch or a recorded walkthrough.
