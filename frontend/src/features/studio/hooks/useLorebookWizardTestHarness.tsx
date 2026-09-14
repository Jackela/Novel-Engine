import { act } from "react";

import type { LoreExtractCandidate } from "@/app/types/lore";
import type { StudioJob } from "@/app/types/studio";
import { createMountHarness } from "@/test/harness";

import { useLorebookWizard } from "./useLorebookWizard";

/**
 * Shared harness for the lorebook wizard hook tests
 * (`useLorebookWizard*.test.tsx`): job fixtures and a mounted-hook reader.
 * Kept outside the vitest test-file glob on purpose; each test file owns
 * its own `@/app/api` mock.
 */

type HookResult = ReturnType<typeof useLorebookWizard>;

/** A complete terminal lore-extract job carrying `candidates`. */
export function loreJob(
  candidates: LoreExtractCandidate[],
  overrides: Partial<StudioJob> = {},
): StudioJob {
  return {
    id: "job-1",
    project_id: "project-1",
    document_id: null,
    kind: "lore-extract",
    operation: "extract",
    status: "completed",
    provider: "mock",
    model: "scripted-model",
    request: {},
    result: { candidates },
    error: null,
    retry_of_job_id: null,
    events: [],
    created_at: "2026-09-14T00:00:00.000Z",
    updated_at: "2026-09-14T00:00:00.000Z",
    ...overrides,
  };
}

/** One candidate suggestion with a derived summary. */
export function candidate(
  kind: LoreExtractCandidate["kind"],
  title: string,
  aliases: string[],
): LoreExtractCandidate {
  return { kind, title, aliases, summary: `${title} summary.` };
}

/** Mount the hook once and expose its latest result. */
export function wizardHookHarness(): {
  readonly mountHarness: ReturnType<typeof createMountHarness>;
  readonly result: () => HookResult;
} {
  const mountHarness = createMountHarness();
  let current: HookResult | undefined;
  function Harness(): null {
    current = useLorebookWizard("project-1", "mock");
    return null;
  }
  mountHarness.mount(<Harness />);
  return {
    mountHarness,
    result: (): HookResult => {
      if (current === undefined) throw new Error("Expected wizard hook result after render.");
      return current;
    },
  };
}

/** Submit one pasted segment through the mounted hook. */
export async function submitSegment(hook: HookResult, text: string): Promise<void> {
  await act(async () => {
    await hook.submitSegment(text, "Pasted text");
  });
}
