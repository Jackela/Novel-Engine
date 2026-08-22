CREATE TABLE `document_revisions` (
	`id` text PRIMARY KEY NOT NULL,
	`document_id` text NOT NULL,
	`parent_revision_id` text,
	`revision_number` integer NOT NULL,
	`content_markdown` text DEFAULT '' NOT NULL,
	`metadata_json` text DEFAULT '{}' NOT NULL,
	`source` text DEFAULT 'author' NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`document_id`) REFERENCES `documents`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `uq_document_revision_number` ON `document_revisions` (`document_id`,`revision_number`);--> statement-breakpoint
CREATE INDEX `idx_document_revisions_document` ON `document_revisions` (`document_id`);--> statement-breakpoint
CREATE TABLE `documents` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`kind` text NOT NULL,
	`title` text NOT NULL,
	`position` integer DEFAULT 0 NOT NULL,
	`current_revision_id` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `uq_document_identity` ON `documents` (`project_id`,`kind`,`title`);--> statement-breakpoint
CREATE INDEX `idx_documents_project_kind` ON `documents` (`project_id`,`kind`);--> statement-breakpoint
CREATE TABLE `projects` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_id` text,
	`guest_session_id` text,
	`title` text NOT NULL,
	`description` text DEFAULT '' NOT NULL,
	`settings_json` text DEFAULT '{}' NOT NULL,
	`import_hash` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`owner_id`) REFERENCES `owners`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`guest_session_id`) REFERENCES `sessions`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `projects_import_hash_unique` ON `projects` (`import_hash`);