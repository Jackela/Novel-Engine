PRAGMA foreign_keys=OFF;--> statement-breakpoint
CREATE TABLE `__new_usage_events` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text DEFAULT '' NOT NULL,
	`job_id` text,
	`provider` text NOT NULL,
	`model` text NOT NULL,
	`prompt_tokens` integer DEFAULT 0 NOT NULL,
	`completion_tokens` integer DEFAULT 0 NOT NULL,
	`outcome` text DEFAULT 'completed' NOT NULL,
	`token_source` text DEFAULT 'provider' NOT NULL,
	`request_evidence_json` text DEFAULT '{}' NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`job_id`) REFERENCES `jobs`(`id`) ON UPDATE no action ON DELETE set null,
	CONSTRAINT "ck_usage_events_outcome" CHECK("__new_usage_events"."outcome" IN ('completed', 'failed')),
	CONSTRAINT "ck_usage_events_token_source" CHECK("__new_usage_events"."token_source" IN ('provider', 'estimated', 'unreported')),
	CONSTRAINT "ck_usage_events_prompt_tokens_safe" CHECK(typeof("__new_usage_events"."prompt_tokens") = 'integer' AND "__new_usage_events"."prompt_tokens" BETWEEN 0 AND 9007199254740991),
	CONSTRAINT "ck_usage_events_completion_tokens_safe" CHECK(typeof("__new_usage_events"."completion_tokens") = 'integer' AND "__new_usage_events"."completion_tokens" BETWEEN 0 AND 9007199254740991)
);
--> statement-breakpoint
INSERT INTO `__new_usage_events`("id", "project_id", "job_id", "provider", "model", "prompt_tokens", "completion_tokens", "outcome", "token_source", "request_evidence_json", "created_at") SELECT "id", "project_id", "job_id", "provider", "model", "prompt_tokens", "completion_tokens", "outcome", "token_source", "request_evidence_json", "created_at" FROM `usage_events`;--> statement-breakpoint
DROP TABLE `usage_events`;--> statement-breakpoint
ALTER TABLE `__new_usage_events` RENAME TO `usage_events`;--> statement-breakpoint
PRAGMA foreign_keys=ON;--> statement-breakpoint
CREATE INDEX `idx_usage_events_project_id` ON `usage_events` (`project_id`);