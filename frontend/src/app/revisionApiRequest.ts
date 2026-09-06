import { apiPath, type PageRequestOptions, pageRequest } from "./pageRequest";

/** Options for one bounded document-revisions page request. */
export type RevisionRequestOptions = PageRequestOptions;

/** Build the document-revisions page request. */
export function documentRevisionsRequest(
  projectId: string,
  documentId: string,
  options: RevisionRequestOptions,
): readonly [path: string, init: RequestInit] {
  return pageRequest(
    apiPath("projects", projectId, "documents", documentId, "revisions"),
    options,
    "Revision page",
  );
}
