DROP INDEX `idx_job_events_job_id`;--> statement-breakpoint
ALTER TABLE `job_events` ADD `sequence` integer DEFAULT 1 NOT NULL;--> statement-breakpoint
WITH `ranked_events` AS (
	SELECT `id`, ROW_NUMBER() OVER (
		PARTITION BY `job_id`
		ORDER BY `rowid` ASC
	) AS `causal_sequence`
	FROM `job_events`
)
UPDATE `job_events`
SET `sequence` = (
	SELECT `causal_sequence`
	FROM `ranked_events`
	WHERE `ranked_events`.`id` = `job_events`.`id`
);--> statement-breakpoint
CREATE UNIQUE INDEX `uq_job_events_job_sequence` ON `job_events` (`job_id`,`sequence`);
