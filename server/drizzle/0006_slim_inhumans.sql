DROP INDEX `projects_import_hash_unique`;--> statement-breakpoint
CREATE UNIQUE INDEX `uq_project_owner_import_hash` ON `projects` (`owner_id`,`import_hash`);--> statement-breakpoint
CREATE UNIQUE INDEX `uq_project_guest_import_hash` ON `projects` (`guest_session_id`,`import_hash`);