DROP INDEX `idx_exports_project_created`;--> statement-breakpoint
CREATE INDEX `idx_exports_project_created_id` ON `exports` (`project_id`,`created_at`,`id`);