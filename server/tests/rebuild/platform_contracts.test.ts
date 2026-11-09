import { Ajv } from "ajv";
import { describe, expect, it } from "vitest";
import {
  DocumentCreateRequest,
  MAX_DOCUMENT_BODY,
  SaveDocumentRequest,
} from "../../src/contracts/documents.js";
import {
  ERROR_CATALOG,
  ERROR_CODE_LIST,
  FRAME_ERROR_CODES,
  remedyFor,
  retryPolicyFor,
  statusFor,
} from "../../src/contracts/errors.js";
import { CredentialsRequest, OwnerView, SessionProbeView } from "../../src/contracts/identity.js";
import {
  PageQuery,
  ProjectCreateRequest,
  ProjectUpdateRequest,
  ProjectView,
} from "../../src/contracts/projects.js";
import {
  PROVIDER_NAMES,
  PROVIDER_STEPS,
  STEP_TEXT_KIND,
  WRITING_LANGUAGES,
} from "../../src/platform/text-generation/ports.js";

const ajv = new Ajv({ allErrors: true, strict: false });

function accepts(schema: object, payload: unknown): boolean {
  const validate = ajv.compile(schema);
  return validate(payload) === true;
}

const validProject = {
  id: "proj-1",
  title: "The Long Winter",
  description: "",
  volumeCount: 0,
  documentCount: 0,
  createdAt: 1_700_000_000_000,
  updatedAt: 1_700_000_000_000,
};

describe("error catalog accessors", () => {
  it("derives status, retry policy, and remedy from the single catalog", () => {
    expect(statusFor("UNAUTHORIZED")).toBe(401);
    expect(statusFor("OPERATION_CAPACITY_EXCEEDED")).toBe(503);
    expect(retryPolicyFor("RATE_LIMIT_EXCEEDED")).toBe("after-delay");
    expect(retryPolicyFor("NOT_FOUND")).toBe("no");
    expect(remedyFor("PROVIDER_NOT_CONFIGURED")).toBe("configure");
    expect(remedyFor("REVISION_CONFLICT")).toBe("reread");
  });

  it("lists every code exactly once", () => {
    expect(new Set(ERROR_CODE_LIST).size).toBe(ERROR_CODE_LIST.length);
    expect([...ERROR_CODE_LIST].sort()).toEqual(Object.keys(ERROR_CATALOG).sort());
  });

  it("never tells a client to retry after a delay on a status that cannot carry one", () => {
    for (const code of ERROR_CODE_LIST) {
      if (ERROR_CATALOG[code].retry !== "after-delay") continue;
      expect([409, 429, 503]).toContain(ERROR_CATALOG[code].status);
    }
  });

  it("only asks for re-authentication on 401 and 403", () => {
    for (const code of ERROR_CODE_LIST) {
      if (ERROR_CATALOG[code].remedy !== "reauth") continue;
      expect([401, 403]).toContain(ERROR_CATALOG[code].status);
    }
  });

  it("keeps transport framing failures out of the catalog", () => {
    // Fastify answers these itself; a catalog entry would silently re-code them.
    expect(ERROR_CODE_LIST).not.toContain("PAYLOAD_TOO_LARGE");
    for (const code of ERROR_CODE_LIST) {
      expect(code.startsWith("FST_ERR")).toBe(false);
    }
  });

  it("gives every frame error a message, retry policy, and remedy but no status", () => {
    for (const definition of Object.values(FRAME_ERROR_CODES)) {
      expect(definition.defaultMessage).not.toBe("");
      expect(["yes", "after-delay", "no"]).toContain(definition.retry);
      expect(definition).not.toHaveProperty("status");
    }
  });
});

describe("provider vocabulary", () => {
  it("keeps client-selectable providers a closed set", () => {
    expect([...PROVIDER_NAMES]).toEqual(["mock", "dashscope", "openai_compatible"]);
  });

  it("classifies every step's text kind and nothing else", () => {
    expect(Object.keys(STEP_TEXT_KIND).sort()).toEqual([...PROVIDER_STEPS].sort());
    expect(STEP_TEXT_KIND.chapter_draft).toBe("prose");
    expect(STEP_TEXT_KIND.editorial_review).toBe("json");
  });

  it("supports exactly the two writing languages DR-023 defines", () => {
    expect([...WRITING_LANGUAGES]).toEqual(["en", "zh"]);
  });
});

describe("wire contracts", () => {
  it("reject unknown fields everywhere a request body is accepted", () => {
    expect(accepts(ProjectCreateRequest, { title: "A", description: "" })).toBe(true);
    expect(accepts(ProjectCreateRequest, { title: "A", description: "", extra: 1 })).toBe(false);
    expect(accepts(CredentialsRequest, { username: "owner", password: "pw" })).toBe(true);
    expect(accepts(CredentialsRequest, { username: "owner", password: "pw", role: "admin" })).toBe(
      false,
    );
  });

  it("enforces the documented caps", () => {
    expect(accepts(ProjectCreateRequest, { title: "", description: "" })).toBe(false);
    expect(accepts(ProjectCreateRequest, { title: "x".repeat(201), description: "" })).toBe(false);
    expect(accepts(ProjectUpdateRequest, { description: null })).toBe(true);
    expect(accepts(PageQuery, { limit: 0 })).toBe(false);
    expect(accepts(PageQuery, { limit: 101 })).toBe(false);
    expect(accepts(PageQuery, { limit: 100 })).toBe(true);
  });

  it("treats a document body at the cap as valid and one code unit over as invalid", () => {
    const base = { contentMarkdown: "x".repeat(MAX_DOCUMENT_BODY), baseRevisionId: null };
    expect(accepts(SaveDocumentRequest, base)).toBe(true);
    expect(
      accepts(SaveDocumentRequest, { ...base, contentMarkdown: "x".repeat(MAX_DOCUMENT_BODY + 1) }),
    ).toBe(false);
  });

  it("requires a kind from the closed document set when creating", () => {
    expect(accepts(DocumentCreateRequest, { kind: "chapter", title: "One" })).toBe(true);
    expect(accepts(DocumentCreateRequest, { kind: "appendix", title: "One" })).toBe(false);
    expect(accepts(DocumentCreateRequest, { kind: "chapter" })).toBe(false);
  });

  it("carries the project timestamps as epoch milliseconds", () => {
    expect(accepts(ProjectView, validProject)).toBe(true);
    expect(accepts(ProjectView, { ...validProject, createdAt: -1 })).toBe(false);
    expect(accepts(ProjectView, { ...validProject, volumeCount: -1 })).toBe(false);
  });

  it("answers the session probe for both authenticated and anonymous states", () => {
    expect(accepts(SessionProbeView, { authenticated: false })).toBe(true);
    expect(
      accepts(SessionProbeView, {
        authenticated: true,
        ownerId: "o-1",
        expiresAt: 1_700_000_000_000,
      }),
    ).toBe(true);
    expect(accepts(SessionProbeView, { authenticated: true, ownerId: "o-1" })).toBe(false);
  });

  it("returns identity only from setup, never a session", () => {
    expect(accepts(OwnerView, { ownerId: "o-1", username: "owner" })).toBe(true);
    expect(accepts(OwnerView, { ownerId: "o-1", username: "owner", token: "t" })).toBe(false);
  });
});
