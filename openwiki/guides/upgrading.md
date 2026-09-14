# Upgrading

Novel Engine is upgraded by pulling the new code and rebuilding the image.
Your manuscripts live in the `novel-engine-data` volume, which an upgrade
never touches, and the studio prepares its own safety backup on every start —
so an upgrade is routine.

## Before you upgrade

Take one copy off the machine with the [backup](backup-and-restore.md)
routine. The studio takes automatic backups on every start, but a copy on an
external drive or in a private cloud folder is the one that saves you from a
disk failure during the upgrade.

## Get the new code

- **If you cloned the repository**: from the checkout folder, run
  `git pull`.
- **If you downloaded the ZIP**: download the new ZIP and unzip it into a
  **new** folder, then copy your `.env` into that folder — it holds your
  provider keys. If you also made a `compose.override.yaml` for structural
  changes such as a different port, copy that too. The old folder can stay
  or be deleted; your data is not in it.

## Rebuild and restart

From the folder containing `compose.yaml`:

```bash
docker compose up -d --build
```

The rebuild takes a few minutes (new code must be compiled into a new image);
watch progress with `docker compose logs -f novel-engine`.

## What happens automatically on the first start

The startup sequence protects your data in a fixed order:

1. **Safety backup** — if a database exists, a timestamped copy is written to
   `backups/` first.
2. **Migrations** — the database schema is brought up to the new version's
   shape, automatically.
3. **Reconciliation** — export records and history word counts are checked
   against the files on disk.
4. **Job recovery** — any generation run that was interrupted by the previous
   shutdown is cleaned up.

Only then does the studio start serving. Your login session survives the
upgrade, because the session secret lives in the data volume.

Confirm the new version at `http://localhost:8000/version` in your browser.

## What an upgrade does not do

- It does not delete or reset data: the volume persists across rebuilds and
  container replacement. The only way to lose the volume is
  `docker compose down -v`.
- It does not transfer anything off your machine.
- It cannot be trivially undone: the database schema moves forward. If you
  must run an older version afterwards, restore the pre-upgrade backup first
  ([backup and restore](backup-and-restore.md#restoring)).

## Upgrading from 0.3.x (the retired Python stack)

Version 0.4.0 was a rewrite cutover, and its database format is unrelated to
the Python era's. A Python-era database cannot be migrated: start 0.4.0 or
later with a fresh data directory, create the Owner account, and re-import
old workspaces with the import command described in the
[README](../../README.md#commands). The pre-cutover code remains at the Git
tag `python-final` for reference.
