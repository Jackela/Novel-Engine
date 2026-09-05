-- Remove only legacy review snapshots that never acquired durable evidence.
-- Deleting the parent cascades to snapshot_documents and releases their
-- document/revision RESTRICT guards; completed reviews and every export stay.
DELETE FROM `project_snapshots`
WHERE `reason` = 'review'
  AND NOT EXISTS (
    SELECT 1
    FROM `reviews`
    WHERE `reviews`.`snapshot_id` = `project_snapshots`.`id`
  )
  AND NOT EXISTS (
    SELECT 1
    FROM `exports`
    WHERE `exports`.`snapshot_id` = `project_snapshots`.`id`
  );
