CREATE TABLE `volumes` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`title` text NOT NULL,
	`position` integer NOT NULL,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `uq_volume_identity` ON `volumes` (`project_id`,`title`);--> statement-breakpoint
CREATE INDEX `idx_volumes_project_position` ON `volumes` (`project_id`,`position`);--> statement-breakpoint
ALTER TABLE `documents` ADD `volume_id` text REFERENCES volumes(id);--> statement-breakpoint
-- Backfill (ADR-0005 default-volume invariant): every existing project gains
-- one deterministic default volume holding its chapters. The id is derived
-- from the project id so re-running against the same row set stays stable;
-- non-chapter documents keep volume_id NULL. Hand-written in the same
-- hand-edited channel as the FTS5 DDL; meta snapshots stay generator-only.
INSERT INTO `volumes` (`id`, `project_id`, `title`, `position`, `created_at`, `updated_at`)
SELECT 'dvol-' || `p`.`id`, `p`.`id`, 'Default Volume', 1, `p`.`created_at`, `p`.`updated_at`
FROM `projects` AS `p`;--> statement-breakpoint
UPDATE `documents`
SET `volume_id` = 'dvol-' || `documents`.`project_id`
WHERE `documents`.`kind` = 'chapter';