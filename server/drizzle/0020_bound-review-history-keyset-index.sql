DROP INDEX `idx_reviews_project_created`;--> statement-breakpoint
CREATE INDEX `idx_reviews_project_created_id` ON `reviews` (`project_id`,`created_at`,`id`);