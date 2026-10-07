/**
 * Direct contract tests for LoreAliasService (#315, #444): alias reads answer
 * for every document with defensively parsed, normalized values; alias and
 * status writes are the write-path normalization contract ("readers always
 * see trimmed, deduped aliases and a closed-set status"). Fakes record the
 * store commands through the ports, so these tests pin what the service
 * sends and echoes — kind and not-found refusals stay the store's.
 */
import { describe, expect, it } from "vitest";
import { LoreAliasService } from "../../src/contexts/studio/application/lore_alias_service.js";
import type {
  DocumentStore,
  DocumentWithCurrent,
} from "../../src/contexts/studio/application/ports/document_store.js";
import type {
  SetLoreAliasesInput,
  SetLoreStatusInput,
  StudioLoreStore,
} from "../../src/contexts/studio/application/ports/lore_store.js";
import type { ProjectScope } from "../../src/contexts/studio/application/ports/studio_store.js";
import { NotFoundError } from "../../src/contexts/studio/domain/exceptions.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";

const PRINCIPAL: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};
const SCOPE: ProjectScope = { ownerId: "owner-1" };
const NOW = new Date("2026-09-03T00:00:00.000Z");

function characterDocument(loreAliasesJson: string): DocumentWithCurrent {
  const revision = {
    id: "revision-1",
    documentId: "document-1",
    parentRevisionId: null,
    revisionNumber: 1,
    contentMarkdown: "Mara keeps the flooded archive.",
    metadataJson: "{}",
    source: "author",
    wordCount: 5,
    createdAt: NOW,
  };
  return {
    id: "document-1",
    projectId: "project-1",
    kind: "character",
    title: "Mara",
    position: 1,
    volumeId: null,
    beatRef: null,
    loreAliasesJson,
    loreStatus: "draft",
    currentRevisionId: revision.id,
    createdAt: NOW,
    updatedAt: NOW,
    currentRevision: revision,
  };
}

interface DocumentRead {
  scope: ProjectScope;
  projectId: string;
  documentId: string;
}

interface FakeDocuments {
  findDocument(scope: ProjectScope, projectId: string, documentId: string): DocumentWithCurrent;
}

interface FakeLore {
  setLoreAliases(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: SetLoreAliasesInput,
  ): DocumentWithCurrent;
  setLoreStatus(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: SetLoreStatusInput,
  ): DocumentWithCurrent;
}

function harness(
  config: { document?: DocumentWithCurrent; documentFailure?: Error; writeFailure?: Error } = {},
) {
  const reads: DocumentRead[] = [];
  const aliasWrites: Array<{
    scope: ProjectScope;
    projectId: string;
    documentId: string;
    input: SetLoreAliasesInput;
  }> = [];
  const statusWrites: Array<{
    scope: ProjectScope;
    projectId: string;
    documentId: string;
    input: SetLoreStatusInput;
  }> = [];
  let clockCalls = 0;
  const documents: FakeDocuments = {
    findDocument: (scope, projectId, documentId) => {
      reads.push({ scope, projectId, documentId });
      if (config.documentFailure !== undefined) throw config.documentFailure;
      return config.document ?? characterDocument("[]");
    },
  };
  const lore: FakeLore = {
    setLoreAliases: (scope, projectId, documentId, input) => {
      aliasWrites.push({ scope, projectId, documentId, input });
      if (config.writeFailure !== undefined) throw config.writeFailure;
      return config.document ?? characterDocument("[]");
    },
    setLoreStatus: (scope, projectId, documentId, input) => {
      statusWrites.push({ scope, projectId, documentId, input });
      if (config.writeFailure !== undefined) throw config.writeFailure;
      return config.document ?? characterDocument("[]");
    },
  };
  const service = new LoreAliasService(
    documents as unknown as DocumentStore,
    lore as unknown as StudioLoreStore,
    () => {
      clockCalls += 1;
      return NOW;
    },
  );
  return {
    service,
    reads,
    aliasWrites,
    statusWrites,
    clockCalls: () => clockCalls,
  };
}

describe("LoreAliasService alias reads (#315)", () => {
  it("reads the stored list owner-scoped and normalizes it defensively", () => {
    const { service, reads, aliasWrites, statusWrites } = harness({
      document: characterDocument('["  The Archivist ", "the archivist", "", " Keeper "]'),
    });

    expect(service.listDocumentLoreAliases(PRINCIPAL, "project-1", "document-1")).toEqual([
      "The Archivist",
      "Keeper",
    ]);
    expect(reads).toEqual([{ scope: SCOPE, projectId: "project-1", documentId: "document-1" }]);
    expect(aliasWrites).toEqual([]);
    expect(statusWrites).toEqual([]);
  });

  it("answers an empty list for unreadable stored alias JSON", () => {
    for (const loreAliasesJson of ["{}", '"text"', "[1,2]", "", "broken", "null"]) {
      const { service } = harness({ document: characterDocument(loreAliasesJson) });
      expect(service.listDocumentLoreAliases(PRINCIPAL, "project-1", "document-1")).toEqual([]);
    }
  });

  it("answers an empty list for a document that never declared aliases", () => {
    const { service } = harness({ document: characterDocument("[]") });
    expect(service.listDocumentLoreAliases(PRINCIPAL, "project-1", "document-1")).toEqual([]);
  });

  it("propagates the store's not-found for a missing document", () => {
    const failure = new NotFoundError("Document not found: ghost.");
    const { service } = harness({ documentFailure: failure });
    let caught: unknown;
    try {
      service.listDocumentLoreAliases(PRINCIPAL, "project-1", "ghost");
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(failure);
  });
});

describe("LoreAliasService alias writes (#315)", () => {
  it("normalizes before persistence and echoes the stored list without reading back", () => {
    const { service, reads, aliasWrites, clockCalls } = harness();

    const payload = service.overwriteDocumentAliases(PRINCIPAL, "project-1", "document-1", {
      aliases: ["  the archivist ", "", "The Archivist", "keeper"],
    });

    expect(aliasWrites).toEqual([
      {
        scope: SCOPE,
        projectId: "project-1",
        documentId: "document-1",
        input: { aliases: ["the archivist", "keeper"], now: NOW },
      },
    ]);
    expect(payload).toEqual({ aliases: ["the archivist", "keeper"] });
    // The write is document-level state: no read-back and no revision is minted.
    expect(reads).toEqual([]);
    expect(clockCalls()).toBe(1);
  });

  it("bounds every stored entry to the schema limits", () => {
    const overlong = "x".repeat(260);
    const many = Array.from({ length: 70 }, (_, index) => `alias-${index}`);
    const { service, aliasWrites } = harness({});
    const second = harness({});

    service.overwriteDocumentAliases(PRINCIPAL, "project-1", "document-1", {
      aliases: [overlong, ...many],
    });
    second.service.overwriteDocumentAliases(PRINCIPAL, "project-1", "document-1", {
      aliases: many,
    });

    const firstWrite = aliasWrites[0]?.input.aliases;
    // An overlong candidate is bounded to the schema's 240 characters rather
    // than refused outright; the request schema already rejects >240 by
    // validation, so this bound only guards direct application callers.
    expect(firstWrite?.[0]).toBe("x".repeat(240));
    expect(firstWrite).toHaveLength(64);
    expect(overlong).toHaveLength(260);
    const capped = second.aliasWrites[0]?.input.aliases ?? [];
    expect(capped).toHaveLength(64);
    expect(capped[0]).toBe("alias-0");
    expect(capped.at(-1)).toBe("alias-63");
  });

  it("surfaces the store's non-lore refusal unchanged", () => {
    const refusal = new InvalidOperationError(
      "Only character and world documents carry lorebook aliases.",
    );
    const { service, clockCalls } = harness({ writeFailure: refusal });
    let caught: unknown;
    try {
      service.overwriteDocumentAliases(PRINCIPAL, "project-1", "note-1", { aliases: ["x"] });
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(refusal);
    // Normalization happens first, so the clock is read before the refusal.
    expect(clockCalls()).toBe(1);
  });
});

describe("LoreAliasService lifecycle status writes (#444)", () => {
  it("writes each closed-enum status with one clock reading and echoes it", () => {
    for (const status of ["draft", "stable", "deprecated"]) {
      const { service, statusWrites, reads, clockCalls } = harness();
      const payload = service.changeDocumentLoreStatus(PRINCIPAL, "project-1", "document-1", {
        status,
      });
      expect(statusWrites).toEqual([
        {
          scope: SCOPE,
          projectId: "project-1",
          documentId: "document-1",
          input: { status, now: NOW },
        },
      ]);
      expect(payload).toEqual({ lore_status: status });
      expect(reads).toEqual([]);
      expect(clockCalls()).toBe(1);
    }
  });

  it("refuses a status outside the closed enum before persistence and without a clock read", () => {
    const { service, statusWrites, clockCalls } = harness();
    for (const status of ["", "STABLE", "archived", "published", "null"]) {
      expect(() =>
        service.changeDocumentLoreStatus(PRINCIPAL, "project-1", "document-1", { status }),
      ).toThrow(
        new InvalidOperationError(
          `Unsupported lore lifecycle status: ${status} (expected draft, stable, or deprecated).`,
        ),
      );
    }
    expect(statusWrites).toEqual([]);
    expect(clockCalls()).toBe(0);
  });

  it("propagates the store's not-found for a status write on a missing document", () => {
    const failure = new NotFoundError("Document not found: ghost.");
    const { service } = harness({ writeFailure: failure });
    let caught: unknown;
    try {
      service.changeDocumentLoreStatus(PRINCIPAL, "project-1", "ghost", { status: "stable" });
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(failure);
  });
});
