/**
 * Hook-level fallback messages (`errors.*`): the caller-supplied readable
 * strings handed to `toErrorMessage` when a failure carries no usable
 * message of its own. They render wherever the owning surface renders its
 * error channel, so they live in the dictionaries and resolve through
 * `translateActive` at failure time. `errors.structureCapacity` completes
 * the #461 capacity refusal with the refusing resource and its limit.
 */
export const enErrors = {
  "errors.loadProject": "Unable to load the project. Please retry.",
  "errors.loadDocument": "Unable to load this document. Please retry.",
  "errors.loadDocumentInconsistent":
    "This document is listed but could not be loaded. Please retry.",
  "errors.churnDocument": "This document changed again while loading. Please retry.",
  "errors.saveDocument": "Unable to save.",
  "errors.refreshDocument": "Unable to refresh the latest document.",
  "errors.loadLatestDocument": "Unable to load the latest document.",
  "errors.overwriteDocument": "Unable to overwrite the latest document.",
  "errors.restoreRevision": "Unable to restore revision.",
  "errors.loadRevisions": "Unable to load revisions.",
  "errors.exportProject": "Unable to export project.",
  "errors.exportDiagnostics": "Unable to export diagnostics.",
  "errors.loadExportHistory": "Unable to load export history.",
  "errors.loadOlderExports": "Unable to load older exports.",
  "errors.missingExportHistory": "Export history is unavailable for this project.",
  "errors.missingReviewHistory": "Review history is unavailable for this project.",
  "errors.missingReviewFindings": "Review findings are unavailable for this review.",
  "errors.loadUsage": "Unable to load usage.",
  "errors.loadStats": "Unable to load writing stats.",
  "errors.loadReviewHistory": "Unable to load review history.",
  "errors.loadOlderReviews": "Unable to load older reviews.",
  "errors.loadReviewFindings": "Unable to load review findings.",
  "errors.createProposal": "Unable to create proposal.",
  "errors.acceptProposal": "Unable to accept proposal.",
  "errors.updateBeat": "Unable to update the chapter beat.",
  "errors.createDocument": "Unable to create document.",
  "errors.reorderDocuments": "Unable to reorder documents.",
  "errors.deleteDocument": "Unable to delete the document.",
  "errors.placeChapter": "Unable to place the chapter.",
  "errors.updateLoreStatus": "Unable to update the lore status.",
  "errors.runReview": "Unable to run review.",
  "errors.retryJob": "Unable to retry job.",
  "errors.loadJobs": "Unable to load jobs.",
  "errors.loadOlderJobs": "Unable to load older jobs.",
  "errors.search": "Search failed.",
  "errors.generateChapter": "Unable to generate the chapter.",
  "errors.revisionCursorLoop": "The revision service repeated its continuation cursor.",
  "errors.settingsIdentity": "Invalid project settings response identity.",
  "errors.exportArtifactMissing": "Export artifact is not available.",
  "errors.structureCapacity": "{resource} limit is {limit}.",
} as const;
