CREATE TABLE `project_snapshots` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`reason` text NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `idx_project_snapshots_project_reason_created` ON `project_snapshots` (`project_id`,`reason`,`created_at`);--> statement-breakpoint
CREATE TABLE `review_issues` (
	`id` text PRIMARY KEY NOT NULL,
	`review_id` text NOT NULL,
	`snapshot_document_id` text NOT NULL,
	`document_id` text,
	`severity` text NOT NULL,
	`code` text NOT NULL,
	`message` text NOT NULL,
	`suggestion` text DEFAULT '' NOT NULL,
	`evidence_json` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`review_id`) REFERENCES `reviews`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`snapshot_document_id`) REFERENCES `snapshot_documents`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`document_id`) REFERENCES `documents`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
CREATE INDEX `idx_review_issues_review_severity_code` ON `review_issues` (`review_id`,`severity`,`code`);--> statement-breakpoint
CREATE INDEX `idx_review_issues_snapshot_document` ON `review_issues` (`snapshot_document_id`);--> statement-breakpoint
CREATE TABLE `reviews` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`snapshot_id` text NOT NULL,
	`provider` text NOT NULL,
	`model` text NOT NULL,
	`summary` text DEFAULT '' NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`snapshot_id`) REFERENCES `project_snapshots`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `idx_reviews_project_created` ON `reviews` (`project_id`,`created_at`);--> statement-breakpoint
CREATE INDEX `idx_reviews_snapshot` ON `reviews` (`snapshot_id`);--> statement-breakpoint
CREATE TABLE `snapshot_documents` (
	`id` text PRIMARY KEY NOT NULL,
	`snapshot_id` text NOT NULL,
	`document_id` text NOT NULL,
	`revision_id` text NOT NULL,
	`document_kind` text NOT NULL,
	`document_title` text NOT NULL,
	`revision_metadata_json` text DEFAULT '{}' NOT NULL,
	`position` integer NOT NULL,
	FOREIGN KEY (`snapshot_id`) REFERENCES `project_snapshots`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`document_id`) REFERENCES `documents`(`id`) ON UPDATE no action ON DELETE restrict,
	FOREIGN KEY (`revision_id`) REFERENCES `document_revisions`(`id`) ON UPDATE no action ON DELETE restrict
);
--> statement-breakpoint
CREATE UNIQUE INDEX `uq_snapshot_document` ON `snapshot_documents` (`snapshot_id`,`document_id`);--> statement-breakpoint
CREATE INDEX `idx_snapshot_documents_snapshot_position` ON `snapshot_documents` (`snapshot_id`,`position`);