-- Remove only legacy export snapshots that never acquired durable evidence.
-- Deleting the parent cascades to snapshot_documents and releases their
-- document/revision RESTRICT guards; completed exports and reviews stay.
DELETE FROM `project_snapshots`
WHERE `reason` = 'export'
  AND NOT EXISTS (
    SELECT 1
    FROM `exports`
    WHERE `exports`.`snapshot_id` = `project_snapshots`.`id`
  )
  AND NOT EXISTS (
    SELECT 1
    FROM `reviews`
    WHERE `reviews`.`snapshot_id` = `project_snapshots`.`id`
  )
  AND NOT EXISTS (
    SELECT 1
    FROM `review_issues`
    INNER JOIN `snapshot_documents`
      ON `snapshot_documents`.`id` = `review_issues`.`snapshot_document_id`
    WHERE `snapshot_documents`.`snapshot_id` = `project_snapshots`.`id`
  );
