CREATE TABLE `exports` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`snapshot_id` text NOT NULL,
	`format` text NOT NULL,
	`relative_path` text NOT NULL,
	`size_bytes` integer NOT NULL,
	`checksum_sha256` text NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`snapshot_id`) REFERENCES `project_snapshots`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `idx_exports_project_created` ON `exports` (`project_id`,`created_at`);--> statement-breakpoint
CREATE INDEX `idx_exports_snapshot` ON `exports` (`snapshot_id`);