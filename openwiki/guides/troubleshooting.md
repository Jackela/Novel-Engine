# Troubleshooting

Symptom-first fixes for the Docker setup. Most problems are one of: a busy
port, a browser quirk, or provider configuration that has not reached the
container.

## The studio does not open on localhost:8000

**Symptom:** `docker compose up -d` runs but the browser cannot connect, or
the container keeps restarting.

Port 8000 may already be used by another application. Move the studio to
port 8001: create a `compose.override.yaml` next to `compose.yaml` with:

```yaml
services:
  novel-engine:
    ports: !override
      - "8001:8000"
```

Then run `docker compose up -d` and open `http://localhost:8001`. (The
`!override` tag needs Docker Compose v2.24+, which current Docker Desktop
ships; alternatively edit `compose.yaml` and change `8000:8000` to
`8001:8000`.)

Still nothing? Read what the container says:

```bash
docker compose logs novel-engine
```

and check the health endpoint on the host port you actually mapped — for
example `http://localhost:8001/health/ready` after the port change above, or
`http://localhost:8000/health/ready` on a default installation. A JSON
answer there means the server itself is fine and the problem is between the
browser and the port.

## I created my account but cannot use the studio (Safari)

Safari can display the studio but has a known rendering limitation in the
frosted-glass visual style, and Safari-specific login troubles are the most
common report. Use **Chrome or Firefox**. Your account and manuscripts are
unaffected by the browser you use.

## Generation fails with a provider error

**Symptom:** Copilot or whole-book generation reports an error the moment it
starts, and `docker compose logs novel-engine` shows a provider failure.

Work through this list:

1. Did you run `docker compose up -d` **after** editing `.env` (or
   `compose.override.yaml`)? A restart alone does not apply new environment
   variables; the container must be recreated.
2. Is the API key complete — no truncation, no stray space — and still valid
   at the provider's console?
3. Does the model name exist at that endpoint (for example `deepseek-chat`
   for DeepSeek, `qwen3.5-flash` for DashScope)?
4. Does the provider account have credit or quota left?
5. To keep writing while you sort it out, switch the project's provider back
   to **Mock (trial — no API key)** in Settings; it always works.

The full setup checklist is in [provider setup](provider-setup.md).

## "The data directory is already owned by another Novel Engine process."

**Symptom:** a `backup`, `restore`, or `doctor` command refuses to run.

The running studio owns the data directory exclusively. Stop it first, run
the command, start it again — the exact sequence is in
[backup and restore](backup-and-restore.md#running-cli-commands-in-docker).
The refusal is by design: it is what prevents two processes from writing to
your manuscript database at once.

## I can't find my novels on disk

They are not in the application folder — they are in the Docker volume
`novel-engine-data` (see
[where your data lives](backup-and-restore.md#where-your-data-physically-lives)).
Confirm it exists with:

```bash
docker volume inspect novel-engine-data
```

If the command answers, your manuscripts are there. `docker compose down`
(never `down -v`) is safe; the volume stays.

## The first start takes forever

Expected, once: the application image is built from source the first time,
which can take a few minutes depending on the machine and network. Later
starts reuse the image and open in seconds; a version
[upgrade](upgrading.md) rebuilds and is slow again once.

## The container restarts endlessly with a secret error

**Symptom:** the container never comes up and
`docker compose logs novel-engine` repeats
`entrypoint: /app/data/.secret is empty; remove it or set SECURITY_SECRET_KEY`.

The auto-generated session secret inside the data volume exists but is empty
(perhaps the volume was restored incompletely). Either delete the broken file
so the next start generates a fresh one:

```bash
docker compose stop novel-engine
docker run --rm -v novel-engine-data:/data alpine rm /data/.secret
docker compose up -d
```

or set `SECURITY_SECRET_KEY` to a long random value in your
`compose.override.yaml` and run `docker compose up -d`. A related refusal:
an explicitly set secret that is too short is rejected at startup with
`SECURITY_SECRET_KEY must be at least 16 characters long` — use a longer
value. (Setting the key counts as an intentional logout: log in again after
the restart.)

## Anything else

1. `docker compose logs novel-engine` — the server log names the failing
   component.
2. `http://localhost:8000/health/ready` — answers JSON when the server can
   reach its database.
3. The `doctor` command reports version, database integrity, and account
   state as JSON; it needs the studio stopped first
   ([sequence](backup-and-restore.md#running-cli-commands-in-docker)).
