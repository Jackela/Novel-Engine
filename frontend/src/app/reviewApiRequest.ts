import { apiPath, type PageRequestOptions, pageRequest } from "./pageRequest";

/** Options for one bounded review-list page request. */
export type ReviewListOptions = PageRequestOptions;

/** Build the review-list page request. */
export function reviewsRequest(
  projectId: string,
  options: ReviewListOptions,
): readonly [path: string, init: RequestInit] {
  return pageRequest(apiPath("projects", projectId, "reviews"), options, "Review page");
}

/** Build the review-detail path. */
export function reviewDetailPath(projectId: string, reviewId: string): string {
  return apiPath("projects", projectId, "reviews", reviewId);
}
