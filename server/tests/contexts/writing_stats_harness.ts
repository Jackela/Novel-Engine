import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import type { WritingStatsSummary } from "../../src/contexts/studio/application/ports/writing_stats.js";
import { WritingStatsService } from "../../src/contexts/studio/application/writing_stats_service.js";
import { DocumentStorePart } from "../../src/contexts/studio/infrastructure/document_store_part.js";
import { JobStorePart } from "../../src/contexts/studio/infrastructure/job_store_part.js";
import { ProjectStorePart } from "../../src/contexts/studio/infrastructure/project_store_part.js";
import { VolumeStorePart } from "../../src/contexts/studio/infrastructure/volume_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

/** The fixed aggregation clock: mid-day UTC, so `today` is 2026-03-15. */
export const NOW = new Date("2026-03-15T12:00:00.000Z");
export const DAY_MS = 86_400_000;

/** `count` distinct words under the unified word-count definition. */
export function wordText(count: number): string {
  return Array.from({ length: count }, (_, index) => `word${index}`).join(" ");
}

export interface WritingStatsHarness {
  cleanup: () => Promise<void>;
  documents: DocumentStorePart;
  jobs: JobStorePart;
  principal: Principal;
  projects: ProjectStorePart;
  scope: ReturnType<typeof scopeForPrincipal>;
  service: WritingStatsService;
  volumes: VolumeStorePart;
}

export async function openWritingStatsHarness(): Promise<WritingStatsHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-writing-stats-"));
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3")).catch(
    async (error: unknown) => {
      await rm(directory, { recursive: true, force: true });
      throw error;
    },
  );
  const cleanup = async (): Promise<void> => {
    try {
      studio.close();
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  };
  try {
    const auth = new AuthService({
      store: new DrizzleAuthStore(studio.db),
      sessionSecret: "writing-stats-test-secret",
      now: () => NOW,
    });
    await auth.configureOwner("stats-owner", "long-test-password");
    const principal = (await auth.createOwnerSession("stats-owner", "long-test-password"))
      .principal;
    const documents = new DocumentStorePart(studio.db);
    const jobs = new JobStorePart(studio.db);
    return {
      cleanup,
      documents,
      jobs,
      principal,
      projects: new ProjectStorePart(studio.db),
      scope: scopeForPrincipal(principal),
      service: new WritingStatsService(documents, jobs, { now: () => NOW }),
      volumes: new VolumeStorePart(studio.db),
    };
  } catch (error) {
    await cleanup();
    throw error;
  }
}

/** One new project without a seed document (ADR-0005 still seeds its volume). */
export function newEmptyProject(harness: WritingStatsHarness): string {
  const { project } = harness.projects.addProject(harness.scope, {
    title: "Stats",
    description: "",
    settingsJson: "{}",
    seed: null,
    now: NOW,
  });
  return project.id;
}

/** Append one revision to a document with the given source and timestamp. */
export function saveRevision(
  harness: WritingStatsHarness,
  projectId: string,
  documentId: string,
  contentMarkdown: string,
  source: "author" | "ai-accepted" | "restore",
  at: Date,
): void {
  const base = harness.documents.findDocument(
    harness.scope,
    projectId,
    documentId,
  ).currentRevisionId;
  harness.documents.advanceDocument(harness.scope, projectId, documentId, {
    contentMarkdown,
    baseRevisionId: base,
    title: null,
    metadataJson: "{}",
    source,
    now: at,
  });
}

/** Seed one chapter document whose first revision is `words` author words. */
export function seedChapter(
  harness: WritingStatsHarness,
  projectId: string,
  title: string,
  words: number,
  at: Date,
): string {
  const volume = harness.volumes.findVolumes(harness.scope, projectId)[0];
  if (volume === undefined) throw new Error("Expected the default volume.");
  return harness.documents.addDocument(harness.scope, projectId, {
    kind: "chapter",
    title,
    contentMarkdown: wordText(words),
    position: 0,
    volumeId: volume.id,
    metadataJson: "{}",
    now: at,
  }).id;
}

/** Record one completed proposal job plus its usage event at `at`. */
export function recordUsage(
  harness: WritingStatsHarness,
  projectId: string,
  at: Date,
  tokens: number,
): void {
  const job = harness.jobs.addJob(harness.scope, {
    projectId,
    documentId: null,
    kind: "proposal",
    operation: "continue",
    status: "completed",
    provider: "mock",
    model: "test-model",
    requestJson: "{}",
    resultJson: "{}",
    error: null,
    eventDetailsJson: "{}",
    now: at,
  });
  harness.jobs.addUsageEvent(harness.scope, {
    projectId,
    jobId: job.id,
    provider: "mock",
    model: "test-model",
    promptTokens: tokens,
    completionTokens: tokens,
    requestEvidenceJson: "{}",
    now: at,
  });
}

export function dayRow(summary: WritingStatsSummary, date: string) {
  const row = summary.daily.find((candidate) => candidate.date === date);
  if (row === undefined) throw new Error(`Missing stats day row: ${date}.`);
  return row;
}

export function usageBucket(summary: WritingStatsSummary, date: string) {
  const bucket = summary.usage.daily.find((candidate) => candidate.date === date);
  if (bucket === undefined) throw new Error(`Missing usage daily bucket: ${date}.`);
  return bucket;
}

/** The trailing `count` UTC-day keys ending at `lastDate` (inclusive). */
export function utcDayKeys(lastDate: string, count: number): string[] {
  const last = Date.parse(`${lastDate}T00:00:00Z`);
  return Array.from({ length: count }, (_, index) =>
    new Date(last - (count - 1 - index) * DAY_MS).toISOString().slice(0, 10),
  );
}
