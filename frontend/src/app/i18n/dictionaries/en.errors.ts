/**
 * Hook-level fallback messages (`errors.*`): the caller-supplied readable
 * strings handed to `toErrorMessage` when a failure carries no usable
 * message of its own. They render wherever the owning surface renders its
 * error channel, so they live in the dictionaries and resolve through
 * `translateActive` at failure time.
 *
 * DR-021: the same family carries the localized error surface. One message
 * per stable envelope code (`errors.code*`, mapped by name in
 * `frontend/src/app/localizeError.ts` against
 * `server/src/shared/domain/error_codes.ts`), the capacity resource nouns the
 * capacity messages interpolate (`errors.resource*`), and the contract-layer
 * resource nouns for the `Invalid <label>.<key>` shapes
 * (`errors.contract*`). Codes with conditional envelope details carry a
 * detail-free second message so a malformed envelope never leaves an
 * unresolved `{placeholder}` visible.
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
  "errors.loadBeats": "Unable to load the outline beats.",
  "errors.createDocument": "Unable to create document.",
  "errors.reorderDocuments": "Unable to reorder documents.",
  "errors.deleteDocument": "Unable to delete the document.",
  "errors.placeChapter": "Unable to place the chapter.",
  "errors.createVolume": "Unable to create the volume.",
  "errors.renameVolume": "Unable to rename the volume.",
  "errors.deleteVolume": "Unable to delete the volume.",
  "errors.reorderVolumes": "Unable to reorder volumes.",
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

  // Stable envelope codes (DR-021).
  "errors.codeUnauthorized": "Your session has expired. Sign in again to continue.",
  "errors.codeForbidden": "You do not have permission to do this.",
  "errors.codeSetupTokenInvalid":
    "This first start needs the one-time setup token from the server log.",
  "errors.codeCsrfTokenMissing":
    "This change was blocked because its security token was missing. Reload the page and retry.",
  "errors.codeCsrfTokenInvalid":
    "This change was blocked because its security token was stale. Sign in again and retry.",
  "errors.codeRateLimited": "Too many attempts. Try again in {seconds} seconds.",
  "errors.codeRateLimitedGeneric": "Too many attempts. Wait a moment and try again.",
  "errors.codeNotFound": "The requested item no longer exists. Refresh and try again.",
  "errors.codeInvalidOperation":
    "The server refused this action for the current state. Refresh the page and check before retrying.",
  "errors.codeExportCapacity":
    "The export exceeds the allowed {resource} (limit {limit}). Reduce the export and retry.",
  "errors.codeExportCapacityGeneric":
    "The export exceeds the allowed size. Reduce the export and retry.",
  "errors.codeGenerationCapacity":
    "The {resource} is too large (limit {limit}). Shorten the manuscript or the reference context and retry.",
  "errors.codeGenerationCapacityGeneric":
    "The generation prompt is too large. Shorten the manuscript or the reference context and retry.",
  "errors.codeImportCapacity":
    "The import exceeds the allowed {resource} (limit {limit}). Split the workspace and retry.",
  "errors.codeImportCapacityGeneric":
    "The import exceeds the allowed size. Split the workspace and retry.",
  "errors.codeStructureCapacity":
    "The {resource} reached its limit ({limit}). Remove some structure before retrying.",
  "errors.codeStructureCapacityGeneric":
    "This change would exceed the project's structure limit. Remove some structure before retrying.",
  "errors.codeValidation":
    "Some submitted fields were rejected ({count}). Check them and resubmit.",
  "errors.codeValidationGeneric": "Some submitted fields were rejected. Check them and resubmit.",
  "errors.codeRevisionConflict":
    "This document changed since it was loaded. Load the latest revision and reapply your edit.",
  "errors.codeVolumeConflict": "A volume with this title already exists. Pick another title.",
  "errors.codeDocumentConflict":
    "A document with this title already exists in this project. Pick another title.",
  "errors.codeSnapshotConflict":
    "This document belongs to an export snapshot and cannot be deleted. Delete that export (or its snapshot) first, then delete the document.",
  "errors.codeOperationInFlight":
    "The same operation is already running. Wait for it to finish before retrying.",
  "errors.codeOperationCapacity":
    "The studio is at its concurrent-work limit ({limit}). Try again in {seconds} seconds.",
  "errors.codeOperationCapacityGeneric":
    "The studio is at its concurrent-work limit. Try again shortly.",
  "errors.codeServiceUnavailable":
    "The service is not available right now. Check the server and retry.",
  "errors.codeInternal":
    "An unexpected server error occurred. Retry; if it persists, quote error {error_id}.",
  "errors.codeInternalGeneric":
    "An unexpected server error occurred. Retry; if it persists, check the server log.",
  "errors.codeProviderFailed":
    "The AI provider request failed (HTTP {status}). Check the provider configuration and retry.",
  "errors.codeProviderNotConfigured":
    "This provider has no API key configured. Add the credential (see the provider setup guide), then retry.",
  "errors.codeProviderFailedGeneric":
    "The AI provider request failed. Check the provider configuration and retry.",
  "errors.codePayloadTooLarge":
    "This chapter is too large to save. Split it into smaller chapters — your draft stays in the editor.",
  "errors.codeUnknown": "The request failed ({code}). Retry; if it persists, report this code.",

  // Capacity resource nouns (server resource catalogs, mapped by name).
  "errors.resourceProjectDocuments": "document count",
  "errors.resourceProjectVolumes": "volume count",
  "errors.resourceVolumeChapters": "chapter count",
  "errors.resourceProjectSettingsBytes": "project settings size",
  "errors.resourceDocumentMetadataBytes": "document metadata size",
  "errors.resourceOutlineBeats": "outline beat count",
  "errors.resourceSourceDocuments": "source document count",
  "errors.resourceSourceBytes": "source text size",
  "errors.resourceArtifactBytes": "export size",
  "errors.resourceManifestBytes": "export manifest size",
  "errors.resourcePromptBytes": "generation prompt size",
  "errors.resourceLoreExtractSegment": "lore extract segment length",
  "errors.resourceStoryBytes": "story text size",
  "errors.resourceChapterBytes": "chapter text size",
  "errors.resourceWorkspaceBytes": "workspace size",
  "errors.resourceChapterCount": "chapter count",
  "errors.resourceDirectoryEntries": "directory entry count",

  // Contract-layer resource nouns for `Invalid <label>.<key>` shapes.
  "errors.contractData":
    "The server returned {resource} data that this screen could not read. Reload the page and try again.",
  "errors.contractDataGeneric":
    "The server returned data that this screen could not read. Reload the page and try again.",
  "errors.contractAlias": "alias",
  "errors.contractChapter": "chapter beat",
  "errors.contractDocument": "document",
  "errors.contractExport": "export",
  "errors.contractJob": "job list",
  "errors.contractLore": "lore extraction",
  "errors.contractOwner": "owner",
  "errors.contractProject": "project list",
  "errors.contractProposal": "proposal stream",
  "errors.contractReview": "review",
  "errors.contractRevision": "revision history",
  "errors.contractSearch": "search",
  "errors.contractSession": "session",
  "errors.contractSetup": "setup",
  "errors.contractUsage": "usage",
  "errors.contractVolume": "volume",
  "errors.contractWriting": "writing stats",
} as const;
