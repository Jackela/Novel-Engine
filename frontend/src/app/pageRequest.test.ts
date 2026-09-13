import { describe, expect, it } from "vitest";

import { projectExportsRequest } from "./exportApiRequest";
import { projectJobsRequest, retryJobRequest } from "./jobApiRequest";
import { reviewDetailPath, reviewsRequest } from "./reviewApiRequest";
import { documentRevisionsRequest } from "./revisionApiRequest";

describe("shared page request builders (#479)", () => {
  it.each([
    ["jobs", projectJobsRequest, "Jobs page"],
    ["reviews", reviewsRequest, "Review page"],
    ["exports", projectExportsRequest, "Export page"],
  ])("validates the shared 1..100 limit for %s requests", (_name, build, subject) => {
    expect(() => build("project-1", { limit: 101 })).toThrow(
      `${subject} limit must be an integer from 1 through 100.`,
    );
  });

  it("encodes every path segment across the bounded builders", () => {
    const [revisions] = documentRevisionsRequest("pro/ject", "doc ument", { limit: 1 });
    expect(revisions).toBe("/api/projects/pro%2Fject/documents/doc%20ument/revisions?limit=1");
    expect(reviewDetailPath("pro/ject", "re view")).toBe(
      "/api/projects/pro%2Fject/reviews/re%20view",
    );
    const [retry] = retryJobRequest("pro/ject", "jo b", "key-1");
    expect(retry).toBe("/api/projects/pro%2Fject/jobs/jo%20b/retry");
  });

  it("appends the optional cursor after the validated limit", () => {
    const [path] = projectExportsRequest("project-1", { limit: 100, cursor: "a/b+=" });
    expect(path).toBe("/api/projects/project-1/exports?limit=100&cursor=a%2Fb%2B%3D");
  });
});
