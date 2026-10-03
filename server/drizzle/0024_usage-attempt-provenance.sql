ALTER TABLE `usage_events` ADD `outcome` text DEFAULT 'completed' NOT NULL;--> statement-breakpoint
ALTER TABLE `usage_events` ADD `token_source` text DEFAULT 'provider' NOT NULL;