DROP INDEX `idx_jobs_project_id`;--> statement-breakpoint
CREATE INDEX `idx_jobs_project_created_id` ON `jobs` (`project_id`,`created_at`,`id`);