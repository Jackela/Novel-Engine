import type { FastifyInstance } from "fastify";

import {
  type CookieJar,
  call,
  type DocumentPayload,
  getDocument,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

export const OUTLINE_CONTENT = [
  "# Outline",
  "",
  "## The Storm",
  "",
  "Rain floods the harbour and Mara finds the washed-up chart.",
  "",
  "### The Archive",
  "",
  "Mara decodes the chart against the drowned maps.",
].join("\n");

export interface BeatView {
  beat: { title: string; content: string } | null;
  /** DR-043: the association catalog the UI selects from. */
  candidates: Array<{ title: string }>;
  /** DR-043: which outline the catalog came from, and how many exist. */
  outline: { document_id: string; title: string; outline_count: number } | null;
}

/** DR-043: the candidate catalog of OUTLINE_CONTENT in document order. */
export const OUTLINE_CANDIDATES = [{ title: "The Storm" }, { title: "The Archive" }];

export function outlineAuthority(
  outline: { id: string; title: string },
  outlineCount = 1,
): BeatView["outline"] {
  return { document_id: outline.id, title: outline.title, outline_count: outlineCount };
}

export async function linkBeat(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
  beat: string | null,
) {
  return call(app, jar, "PUT", `/api/projects/${projectId}/documents/${documentId}/beat`, { beat });
}

export async function readBeat(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
): Promise<{ status: number; view?: BeatView }> {
  const response = await call(
    app,
    jar,
    "GET",
    `/api/projects/${projectId}/documents/${documentId}/beat`,
  );
  if (response.statusCode !== 200) {
    return { status: response.statusCode };
  }
  return { status: response.statusCode, view: response.json() as BeatView };
}

/** Fresh chapter + outline pair inside a new project. */
export async function seedChapterWithOutline(
  app: FastifyInstance,
  jar: CookieJar,
): Promise<{ projectId: string; chapter: DocumentPayload; outline: DocumentPayload }> {
  const project = await seedProject(app, jar, "Beat Studio");
  const outline = await seedDocument(app, jar, project.id, {
    kind: "outline",
    title: "Outline",
    content_markdown: OUTLINE_CONTENT,
  });
  const chapter = project.documents[0];
  if (chapter === undefined) throw new Error("expected seeded document");
  return {
    projectId: project.id,
    chapter: await getDocument(app, jar, project.id, chapter.id),
    outline,
  };
}
