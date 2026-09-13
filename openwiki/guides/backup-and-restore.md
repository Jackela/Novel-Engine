# Backup and restore

Your manuscripts are a single SQLite file on your machine, inside a Docker
volume you own. Nothing is stored on anyone else's server, and nothing
prevents you from taking a copy: this page shows the supported ways to back
that file up and to put a copy back.

## Where your data physically lives

With Docker Compose, all state lives in the **named volume**
`novel-engine-data`, mounted inside the container at `/app/data`:

| Path in the volume | Contents |
|---|---|
| `novel-engine.sqlite3` | The database — every project, chapter, revision, and setting. This is the manuscript. |
| `backups/` | Timestamped safety copies (`.sqlite3.bak`) written by you and by the studio itself. |
| `exports/` | Archived copies of your Markdown/DOCX/EPUB exports. |
| `.secret` | The session secret generated on first start (sessions survive restarts because of it). |

The volume survives `docker compose stop`, `docker compose down`, container
removal, rebuilds, and [upgrades](upgrading.md). Only
`docker compose down -v` deletes it — **permanently**. Avoid `-v` the way you
would avoid `rm` on a manuscript folder.

You can see where Docker keeps the volume on disk with
`docker volume inspect novel-engine-data`, but you never need to go there:
use the commands below instead.

## Running CLI commands in Docker

The studio image contains the same command-line tool the server itself uses.
One rule matters: **backup and restore take exclusive ownership of the data
directory**, and the running studio already holds it. Stop the studio first,
run the command, start the studio again:

```bash
docker compose stop novel-engine
docker compose run --rm novel-engine node server/dist/apps/cli/main.js <command>
docker compose start novel-engine
```

If you forget the stop step, the command refuses with
"The data directory is already owned by another Novel Engine process." and
changes nothing.

## Backing up

```bash
docker compose stop novel-engine
docker compose run --rm novel-engine node server/dist/apps/cli/main.js backup
docker compose start novel-engine
```

The `backup` command writes a consistent online backup beneath the backups
directory and prints its path, for example:

```text
/app/data/backups/novel-engine-20260913T093000123Z.sqlite3.bak
```

On an empty installation with no database yet, it instead prints
`No database exists yet.` and writes nothing.

Get the copy out of Docker onto your host, into a folder such as
`novel-engine-backups`:

```bash
docker compose cp novel-engine:/app/data/backups/. ./novel-engine-backups/
```

`docker compose cp` needs the service container to exist — it does after a
`stop`; a `down` removes it, so copy before a `down`. Keep copies outside the
machine when you can: an external drive or any private cloud folder. A backup
that only lives next to the original is not a backup.

The studio also protects you implicitly: **every start** writes one
timestamped safety backup before touching the database (that is how
migrations and upgrades stay reversible — see [upgrading](upgrading.md)).
Old backups are never removed automatically; prune the `backups/` directory
yourself once in a while.

## Restoring

`restore --input BACKUP` verifies a backup file, backs up the current
database, then replaces it atomically. Run it against a backup that is
already in the volume:

```bash
docker compose stop novel-engine
docker compose run --rm novel-engine node server/dist/apps/cli/main.js restore \
  --input /app/data/backups/novel-engine-20260913T093000123Z.sqlite3.bak
docker compose start novel-engine
```

To restore from a copy on your host machine, copy it into the volume first
and continue as above:

```bash
docker compose cp ./novel-engine-backups/my-backup.sqlite3.bak \
  novel-engine:/app/data/backups/
```

A successful restore reports each step:

```text
Verifying restore input: /app/data/backups/novel-engine-20260913T093000123Z.sqlite3.bak
Backed up the replaced database: /app/data/backups/novel-engine-20260913T100001456Z.sqlite3.bak
Restored the database: /app/data/novel-engine.sqlite3
```

Behavior you can rely on:

- The input is integrity-checked first. A missing, empty, or corrupt file
  **refuses the restore and touches nothing**.
- The database being replaced gets its own safety backup first — the restore
  itself is undoable.
- The replacement is atomic; a failed restore never leaves a half-written
  database.
- Restoring a database different from the running one counts as an intentional
  logout: log in again after the studio restarts.

## Manual copy: the last resort

If you only need the raw database file — for example to move to a machine
without this guide — stop the studio and copy the file out of the volume:

```bash
docker compose stop novel-engine
docker run --rm -v novel-engine-data:/data -v "$PWD:/host" alpine \
  cp /data/novel-engine.sqlite3 /host/
docker compose start novel-engine
```

Copying the file back in works the same way in reverse. Prefer the `restore`
command whenever a `.bak` file exists: it verifies what a bare copy cannot.
Copy files only while the studio is stopped. The `-v "$PWD:/host"` mount
syntax is for macOS and Linux terminals; on Windows, move the file with
`docker compose cp` instead (shown under "Backing up" and "Restoring").
