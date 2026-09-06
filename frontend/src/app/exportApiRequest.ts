import { apiPath, type PageRequestOptions, pageRequest } from "./pageRequest";

/** Options for one bounded project-exports page request. */
export type ExportsRequestOptions = PageRequestOptions;

/** Build the project-exports page request. */
export function projectExportsRequest(
  projectId: string,
  options: ExportsRequestOptions,
): readonly [path: string, init: RequestInit] {
  return pageRequest(apiPath("projects", projectId, "exports"), options, "Export page");
}
