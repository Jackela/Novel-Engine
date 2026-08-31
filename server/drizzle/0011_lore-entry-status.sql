ALTER TABLE `documents` ADD `lore_status` text DEFAULT 'draft' NOT NULL;
--> statement-breakpoint
-- Backfill (#444, ADR-0006): every pre-existing lore-kind entry is the
-- author's already-approved canon, so it must stay injectable after the
-- gating lands. SQLite applies ADD COLUMN defaults lazily at read time —
-- without this UPDATE the pre-existing rows would read as `draft` and silently
-- drop out of injection. Static, parameter-free data statement; the row set is
-- pinned by the literal kind list, never by user input.
UPDATE `documents` SET `lore_status` = 'stable' WHERE `kind` IN ('character', 'world');
