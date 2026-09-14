import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import type {
  TextGenerationProviderFactory,
  TextGenerationResult,
  TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { LoreExtractService } from "../../src/contexts/studio/application/lore_extract_service.js";
import type { StudioJobLedgerStore } from "../../src/contexts/studio/application/ports/job_ledger_store.js";
import type { ProjectScope } from "../../src/contexts/studio/application/ports/studio_store.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { JobStorePart } from "../../src/contexts/studio/infrastructure/job_store_part.js";
import { ProjectStorePart } from "../../src/contexts/studio/infrastructure/project_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

/**
 * Shared harness for the lorebook initialization wizard tests
 * (`lorebook_init_*.test.ts`): one hermetic studio database, one owner
 * principal with a seeded project, and the extraction service wired to a
 * caller-supplied provider factory. Kept outside the vitest test-file glob
 * on purpose; the file-size gate measures each test file separately (#440).
 */

/** One scripted provider, recording every task it received. */
export function scriptedFactory(
  handler: (task: TextGenerationTask) => Promise<TextGenerationResult>,
): { calls: TextGenerationTask[]; factory: TextGenerationProviderFactory } {
  const calls: TextGenerationTask[] = [];
  return {
    calls,
    factory: () => ({
      async generateStructured(task) {
        calls.push(task);
        return handler(task);
      },
    }),
  };
}

export function candidateResult(candidates: unknown): TextGenerationResult {
  return {
    step: "lore_extract",
    provider: "mock",
    model: "scripted-model",
    rawText: "",
    content: { candidates },
    promptTokens: null,
    completionTokens: null,
  };
}

export function resultCandidates(payload: Record<string, unknown>): unknown[] {
  const result = payload.result as { candidates?: unknown } | undefined;
  return Array.isArray(result?.candidates) ? (result?.candidates as unknown[]) : [];
}

export function usageRequests(
  jobs: StudioJobLedgerStore,
  scope: ProjectScope,
  projectId: string,
): number {
  return jobs.aggregateProjectUsage(scope, projectId, new Date()).requestCount;
}

export interface LorebookInitHarness {
  cleanup: () => Promise<void>;
  jobs: JobStorePart;
  principal: Awaited<ReturnType<AuthService["createOwnerSession"]>>["principal"];
  projectId: string;
  scope: ProjectScope;
  service: LoreExtractService;
}

export async function openLorebookInitHarness(
  factory: TextGenerationProviderFactory,
): Promise<LorebookInitHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-lorebook-init-"));
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const cleanup = async (): Promise<void> => {
    studio.close();
    await rm(directory, { recursive: true, force: true });
  };
  try {
    const now = new Date("2026-09-14T00:00:00.000Z");
    const jobs = new JobStorePart(studio.db);
    const auth = new AuthService({
      store: new DrizzleAuthStore(studio.db),
      sessionSecret: "lore-extract-test-secret",
      now: () => now,
    });
    await auth.configureOwner("lore-owner", "long-test-password");
    const { principal } = await auth.createOwnerSession("lore-owner", "long-test-password");
    const scope = scopeForPrincipal(principal);
    const { project } = new ProjectStorePart(studio.db).addProject(scope, {
      title: "Lore wizard",
      description: "",
      settingsJson: "{}",
      seed: null,
      now,
    });
    const service = new LoreExtractService(jobs, factory, () => now);
    return { cleanup, jobs, principal, projectId: project.id, scope, service };
  } catch (error) {
    await cleanup();
    throw error;
  }
}
