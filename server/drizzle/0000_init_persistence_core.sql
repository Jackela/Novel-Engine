CREATE TABLE `job_events` (
	`id` text PRIMARY KEY NOT NULL,
	`job_id` text NOT NULL,
	`status` text NOT NULL,
	`details_json` text DEFAULT '{}' NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`job_id`) REFERENCES `jobs`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `idx_job_events_job_id` ON `job_events` (`job_id`);--> statement-breakpoint
CREATE TABLE `jobs` (
	`id` text PRIMARY KEY NOT NULL,
	`kind` text NOT NULL,
	`operation` text NOT NULL,
	`status` text NOT NULL,
	`error` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	`started_at` integer,
	`finished_at` integer
);
--> statement-breakpoint
CREATE INDEX `idx_jobs_status` ON `jobs` (`status`);--> statement-breakpoint
CREATE TABLE `sessions` (
	`id` text PRIMARY KEY NOT NULL,
	`kind` text NOT NULL,
	`owner_id` text,
	`token_hash` text NOT NULL,
	`csrf_token` text,
	`created_at` integer NOT NULL,
	`expires_at` integer,
	`last_seen_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `sessions_token_hash_unique` ON `sessions` (`token_hash`);--> statement-breakpoint
-- Hand-written FTS5 zone: virtual tables, their triggers, and manual row
-- cleanup live as hand-edited SQL inside migration files and never enter the
-- ORM metadata (ADR-0002; drizzle-orm has no CREATE VIRTUAL TABLE DDL).
-- Placeholder schema mirroring the Python content authority; the search
-- feature (#267) grows triggers and columns through later migrations.
CREATE VIRTUAL TABLE IF NOT EXISTS `document_search` USING fts5(document_id UNINDEXED, project_id UNINDEXED, title, content);