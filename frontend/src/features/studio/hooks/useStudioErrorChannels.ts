import { combineErrorMessages, useOwnerKeyedErrors } from "./useOwnerKeyedErrors";

const DOCUMENT_ERROR_SOURCES = ["draft", "proposal", "revision", "restore"] as const;
const PROJECT_ERROR_SOURCES = [
  "jobs",
  "search",
  "review",
  "settings",
  "retryJob",
  "createDocument",
  "moveDocument",
] as const;

export function useStudioErrorChannels(
  projectId: string,
  documentId: string | null,
  sharedError: string | null,
) {
  const projectErrors = useOwnerKeyedErrors(projectId, PROJECT_ERROR_SOURCES);
  const documentErrors = useOwnerKeyedErrors(
    `${projectId}\u0000${documentId ?? ""}`,
    DOCUMENT_ERROR_SOURCES,
  );
  const projectErrorWithoutSettings = combineErrorMessages(
    projectErrors.errors.jobs,
    projectErrors.errors.search,
    projectErrors.errors.review,
    projectErrors.errors.retryJob,
    projectErrors.errors.createDocument,
    projectErrors.errors.moveDocument,
  );
  return {
    projectErrors,
    documentErrors,
    visibleError: combineErrorMessages(documentErrors.error, projectErrors.error, sharedError),
    visibleErrorWithoutSettings: combineErrorMessages(
      documentErrors.error,
      projectErrorWithoutSettings,
      sharedError,
    ),
  };
}
