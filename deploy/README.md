# Deploy Novel Engine from the published image

This directory ships the image-based Compose file used to run Novel Engine
without cloning the repository: `compose.yaml` pulls the prebuilt image from
GHCR and starts the studio in one command. It is the no-build counterpart of
the repository-root `compose.yaml`, which builds the image from source — the
environment pass-through, named volume, healthcheck, and restart policy are
kept identical between the two files.

## Start with one command

Once the v0.8.0 release is published, run this from any empty directory on a
machine with Docker (Compose v2) and an internet connection:

```bash
curl -fsSL https://raw.githubusercontent.com/Jackela/Novel-Engine/v0.8.0/deploy/compose.yaml | docker compose -f - up -d
```

The image (`ghcr.io/jackela/novel-engine`, tag `0.8.0` by default) is pulled
automatically, the studio listens on port 8000, and the first start needs no
manual configuration: the container generates a session secret into the
persistent volume, applies database migrations, and then serves the app. Open
`http://localhost:8000`, create the Owner account on the setup screen, and log
in. The built-in `mock` AI provider works out of the box.

On Windows PowerShell, use `curl.exe` — the plain `curl` name is an alias for
`Invoke-WebRequest` and does not accept these flags:

```powershell
curl.exe -fsSL https://raw.githubusercontent.com/Jackela/Novel-Engine/v0.8.0/deploy/compose.yaml | docker compose -f - up -d
```

Because the Compose file arrives on stdin, the compose project (and with it
the data volume name) is derived from the directory you run the command in.
Start once from a dedicated directory and re-run every future command from
that same directory — see [Data volume](#data-volume).

## Configuration

All settings flow through environment variables, mirroring the repository
`compose.yaml`. Two ways to set them, both applied when you run the command:

- **Shell environment** — export variables before running the one-liner
  (`export LLM_PROVIDER=dashscope`, …). Shell values win.
- **`.env` file** — write the variables into a file named `.env` in the
  directory you run the one-liner from; Compose interpolates from it.

The most common settings:

| Variable | Default | Notes |
|---|---|---|
| `NE_VERSION` | `0.8.0` | Image tag to run; use the release version you want (e.g. `NE_VERSION=0.8.1`). |
| `SECURITY_SECRET_KEY` | empty | Empty lets the container generate and persist a secret in the volume. An explicit value must be at least 16 characters. |
| `SECURITY_CORS_ORIGINS` | placeholder | Comma-separated browser origins; see [Hosting on a server](#hosting-on-a-server). |
| `LLM_PROVIDER` | `mock` | `mock`, `dashscope`, or `openai_compatible`. |
| `DASHSCOPE_API_KEY` / `LLM_API_KEY` | unset | Provider credentials, required for real providers. |

The full variable reference lives in the root
[README Configuration table](../README.md#configuration), and the
[provider setup guide](../openwiki/guides/provider-setup.md) walks through
connecting DashScope or an OpenAI-compatible endpoint.

If you outgrow the one-liner — a different host port, a pinned local copy —
save the file once and switch to regular Compose workflows:

```bash
curl -fsSL https://raw.githubusercontent.com/Jackela/Novel-Engine/v0.8.0/deploy/compose.yaml -o compose.yaml
docker compose up -d
```

From that folder you can add a `compose.override.yaml` (for example the
`ports: !override` snippet from the root README) and use the standard guides.

## Upgrades

Novel Engine releases are image tags, so an upgrade is a pull plus a restart.
Re-run the start command for the newer release — each release's
`deploy/compose.yaml` defaults to its own version — or pin the version with
`NE_VERSION` (on Windows PowerShell set it with `$env:NE_VERSION = "0.8.1"`
and keep `curl.exe`):

```bash
export NE_VERSION=0.8.1
curl -fsSL https://raw.githubusercontent.com/Jackela/Novel-Engine/v0.8.1/deploy/compose.yaml | docker compose -f - up -d
```

For the saved-file variant, update `NE_VERSION` in `compose.yaml` and run
`docker compose up -d` again; Compose pulls the new image and recreates the
container. Run the command from the same directory as the original install,
otherwise Compose creates a new project with an empty volume.

What the upgrade does to your data, in the startup's fixed order:

1. **Safety backup** — before anything changes, the existing database is
   copied to a timestamped file in `backups/` inside the data volume.
2. **Migrations** — the database schema is brought to the new version's
   shape, automatically.
3. **Reconciliation and job recovery** — then the studio starts serving.

Your manuscripts live in the data volume, which an upgrade never touches, and
the login session survives because the secret persists in the same volume.
One caution from the [upgrading guide](../openwiki/guides/upgrading.md): the
schema moves forward only. If you must go back to an older version, restore
the pre-upgrade backup first — and take one copy of your data off the machine
before a major upgrade.

## Hosting on a server

The container runs with `APP_ENVIRONMENT=production`, so the server's
production startup guards apply and fail fast on misconfiguration. For a
demo or public host, mind these points:

- **Reverse proxy with TLS.** The app serves plain HTTP on port 8000. Put a
  reverse proxy (nginx, Caddy, …) in front, terminate TLS there, and forward
  to the container. Do not expose port 8000 directly to the internet: publish
  it to loopback only (`127.0.0.1:8000:8000` in an override file) or firewall
  it, so the only public entry is the encrypted proxy route.
- **Trusted proxies.** Set `SECURITY_TRUSTED_PROXIES` to your proxy's address
  (exact IP, CIDR, or host; comma-separated for several) so the server trusts
  forwarded client identity — this is what keeps per-client rate limiting
  meaningful behind a proxy.
- **Explicit session secret.** The first-boot secret bootstrap (generated
  into the volume) satisfies the production guard, but on a public host set
  `SECURITY_SECRET_KEY` explicitly — for example `openssl rand -hex 32` — so
  the credential is operator-owned and survives even a volume reset. Any
  explicit value must be at least 16 characters; shorter values refuse to
  start.
- **Real CORS origins.** The startup guard rejects wildcard origins and any
  `localhost`/`127.0.0.1` origin in production. When the browser reaches the
  API from a different origin than the one serving it, `SECURITY_CORS_ORIGINS`
  must list those exact origins (scheme + host + port, comma-separated). With
  a same-origin reverse proxy setup — the studio SPA and the API behind one
  hostname — no cross-origin access occurs and the default is never exercised
  by the browser; still, replace the placeholder with your real origin so the
  configuration states the truth.

## Data volume

Everything stateful lives in the named volume `novel-engine-data`, mounted at
`/app/data` in the container:

- `novel-engine.sqlite3` — the SQLite database (the content authority),
- `backups/` — timestamped automatic backups taken before every migration,
- `.secret` — the generated session secret (mode 0600).

`docker compose down` keeps the volume; `docker compose down -v` deletes it
permanently — that is the only routine way to lose your novels. Find the
volume on disk with `docker volume inspect <project>_novel-engine-data`
(the prefix is the directory name you ran the one-liner from, which is why
upgrades must re-run from the same directory). For backups you can restore,
follow the [backup and restore guide](../openwiki/guides/backup-and-restore.md).
