CREATE TABLE `usage_events` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text DEFAULT '' NOT NULL,
	`job_id` text,
	`provider` text NOT NULL,
	`model` text NOT NULL,
	`prompt_tokens` integer DEFAULT 0 NOT NULL,
	`completion_tokens` integer DEFAULT 0 NOT NULL,
	`request_evidence_json` text DEFAULT '{}' NOT NULL,
	`estimated_cost` real,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`job_id`) REFERENCES `jobs`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
CREATE INDEX `idx_usage_events_project_id` ON `usage_events` (`project_id`);--> statement-breakpoint
ALTER TABLE `jobs` ADD `project_id` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `jobs` ADD `document_id` text;--> statement-breakpoint
ALTER TABLE `jobs` ADD `provider` text DEFAULT 'mock' NOT NULL;--> statement-breakpoint
ALTER TABLE `jobs` ADD `model` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `jobs` ADD `request_json` text DEFAULT '{}' NOT NULL;--> statement-breakpoint
ALTER TABLE `jobs` ADD `result_json` text DEFAULT '{}' NOT NULL;--> statement-breakpoint
ALTER TABLE `jobs` ADD `retry_of_job_id` text;--> statement-breakpoint
CREATE INDEX `idx_jobs_project_id` ON `jobs` (`project_id`);