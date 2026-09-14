import { describe, expect, it } from "vitest";

import { capturingFactory } from "./proposal_test_helpers.js";
import {
  admitProposal,
  buildStudioApp,
  call,
  draftProposal,
  getDocument,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

/** The fixed aggregation clock: mid-day UTC, so `today` is 2026-03-15. */
const NOW = new Date("2026-03-15T12:00:00.000Z");

/** `count` distinct words under the unified word-count definition. */
function wordText(count: number): string {
  return Array.from({ length: count }, (_, index) => `word${index}`).join(" ");
}

/** The trailing UTC-day keys of the stats window, oldest first. */
function utcDayKeys(): string[] {
  return Array.from({ length: 30 }, (_, index) =>
    new Date(NOW.getTime() - (29 - index) * 86_400_000).toISOString().slice(0, 10),
  );
}

describe("project writing statistics surface (#653 T2)", () => {
  it("answers 401 unauthenticated and 404 for an unknown project", async () => {
    const { app } = await buildStudioApp(() => NOW);
    try {
      const jar = await ownerJar(app);
      await seedProject(app, jar, "Scoped");

      const anonymous = await app.inject({
        method: "GET",
        url: "/api/projects/p-1/stats",
      });
      expect(anonymous.statusCode).toBe(401);
      expect(anonymous.json().error.code).toBe("UNAUTHORIZED");

      const unknown = await call(
        app,
        jar,
        "GET",
        "/api/projects/00000000-0000-0000-0000-000000000000/stats",
      );
      expect(unknown.statusCode).toBe(404);
      expect(unknown.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });

  it("returns defined zero states for a project without revisions or usage", async () => {
    const { app } = await buildStudioApp(() => NOW);
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Blank slate");
      const seeded = project.documents[0];
      if (seeded === undefined) throw new Error("Expected the Chapter 1 seed document.");
      // The only history is the seed revision; remove it so the project is
      // truly empty — no revisions, no structure, no usage events.
      const removed = await call(
        app,
        jar,
        "DELETE",
        `/api/projects/${project.id}/documents/${seeded.id}`,
      );
      expect(removed.statusCode, removed.body).toBe(204);

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/stats`);
      expect(response.statusCode, response.body).toBe(200);
      expect(response.json()).toEqual({
        project_id: project.id,
        daily: utcDayKeys().map((date) => ({
          date,
          words: { author: 0, ai_accepted: 0, restore: 0 },
        })),
        weekly: expect.any(Array),
        streak_days: 0,
        chapters: { total: 0, started: 0 },
        usage: {
          project_id: project.id,
          request_count: 0,
          prompt_tokens: 0,
          completion_tokens: 0,
          per_model: [],
          daily: utcDayKeys().map((date) => ({
            date,
            request_count: 0,
            prompt_tokens: 0,
            completion_tokens: 0,
          })),
        },
      });
      const body = response.json();
      expect(body.weekly).toHaveLength(4);
      for (const week of body.weekly) {
        expect(week.words).toEqual({ author: 0, ai_accepted: 0, restore: 0 });
      }
    } finally {
      await app.close();
    }
  });

  it("maps the aggregation's source split and reuses the usage aggregation verbatim", async () => {
    const acceptedWords = 800;
    const capture = capturingFactory({ markdown: wordText(acceptedWords) });
    const { app } = await buildStudioApp(() => NOW, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Attribution");
      const seededSummary = project.documents[0];
      if (seededSummary === undefined) throw new Error("Expected the Chapter 1 seed document.");
      const seeded = await getDocument(app, jar, project.id, seededSummary.id);

      // Author saves lift the chapter from the 2-word seed to 500 words.
      const saved = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/documents/${seeded.id}`,
        {
          content_markdown: wordText(500),
          base_revision_id: seeded.current_revision_id,
        },
      );
      expect(saved.statusCode, saved.body).toBe(200);
      // Accepting the proposal replaces 500 words with 800: an `ai-accepted`
      // delta of +300 on the same UTC day.
      const proposal = await draftProposal(app, jar, project.id, seeded.id, {
        operation: "continue",
      });
      const accepted = await admitProposal(app, jar, project.id, proposal.id);
      expect(accepted.status).toBe("completed");

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/stats`);
      expect(response.statusCode, response.body).toBe(200);
      const body = response.json();

      // The seed (2) plus the author save (+498) attribute 500 author words
      // to today; the accepted proposal adds 300 more as accepted text.
      const today = body.daily.at(-1);
      expect(today).toMatchObject({
        date: "2026-03-15",
        words: { author: 500, ai_accepted: 300, restore: 0 },
      });
      expect(body.streak_days).toBe(1);
      expect(body.chapters).toEqual({ total: 1, started: 1 });
      // The newest whole week sums its seven UTC days.
      expect(body.weekly.at(-1).words).toEqual({ author: 500, ai_accepted: 300, restore: 0 });

      // The usage member is the usage aggregation's own payload, field for
      // field — one accounting path, never a second.
      const usage = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(usage.statusCode, usage.body).toBe(200);
      expect(body.usage).toEqual(usage.json());
    } finally {
      await app.close();
    }
  });
});
