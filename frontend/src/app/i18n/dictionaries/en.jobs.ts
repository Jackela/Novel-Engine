/**
 * Jobs panel messages (DR-010: the lazily read proposal text behind a
 * completed proposal row). A separate chunk so the studio dictionary stays
 * inside the file-size budget; `zh.jobs.ts` mirrors this key set.
 */
export const enJobs = {
  "jobs.heading": "Jobs",
  "jobs.hint": "Durable operation status.",
  "jobs.action.refresh": "Refresh jobs",
  "jobs.action.refreshing": "Refreshing jobs",
  "jobs.action.retry": "Retry {operation}",
  "jobs.action.retrying": "Retrying {operation}",
  "jobs.action.retryTitle": "Retry job",
  "jobs.action.loadOlder": "Load older jobs",
  "jobs.action.loadingOlder": "Loading older jobs",
  "jobs.empty": "No jobs yet.",
  "jobs.row.meta": "{provider} · {date}",
  "jobs.proposal.copy": "Copy",
  "jobs.proposal.error": "Unable to load this proposal.",
  "jobs.proposal.loading": "Loading proposal text…",
  "jobs.proposal.view": "View proposal text",
  // DR-021: the server's raw failure report (English, may quote provider HTTP
  // details) lives behind this disclosure; the visible line stays localized.
  "jobs.error.failed": "This job failed.",
  "jobs.error.technicalDetails": "Technical details",
};
