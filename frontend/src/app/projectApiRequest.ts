import { apiPath, type PageRequestOptions, pageRequest } from "./pageRequest";

/** Options for one bounded project-catalog page request. */
export type ProjectsRequestOptions = PageRequestOptions;

/** Build the project-catalog page request. */
export function projectCatalogRequest(
  options: ProjectsRequestOptions,
): readonly [path: string, init: RequestInit] {
  return pageRequest(apiPath("projects"), options, "Project page");
}
