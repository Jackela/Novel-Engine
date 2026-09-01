CREATE TABLE `export_publication_cleanup_intents` (
	`publication_id` text PRIMARY KEY NOT NULL,
	`artifact_id` text NOT NULL,
	`project_id` text NOT NULL,
	`version` integer NOT NULL,
	`format` text NOT NULL,
	`relative_path` text NOT NULL,
	`stage_file` text NOT NULL,
	`stage_device` text NOT NULL,
	`stage_inode` text NOT NULL,
	`manifest_device` text NOT NULL,
	`manifest_inode` text NOT NULL,
	`size_bytes` integer NOT NULL,
	`checksum_sha256` text NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `idx_export_cleanup_intents_project` ON `export_publication_cleanup_intents` (`project_id`);