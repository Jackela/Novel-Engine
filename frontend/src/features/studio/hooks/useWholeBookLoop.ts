import { useCallback, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { api } from '@/app/api';
import type { Project, StudioDocument } from '@/app/types/studio';

import type { WholeBookChapter } from './wholeBookPlan';

/**
 * #318 whole-book loop state machine: idle → running(current,total) →
 * done(generated, stoppedEarly) | failed(generated, chapter, message).
 * Terminal phases carry how many chapters this run accepted so the control
 * can report preserved work after a stop or failure.
 */
export type WholeBookPhase =
  | { readonly kind: 'idle' }
  | { readonly kind: 'running'; readonly current: number; readonly total: number }
  | { readonly kind: 'done'; readonly generated: number; readonly stoppedEarly: boolean }
  | {
      readonly kind: 'failed';
      readonly generated: number;
      readonly failedChapterTitle: string;
      readonly message: string;
    };

interface UseWholeBookLoopArgs {
  readonly projectId: string;
  readonly provider: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly loadJobs: () => void;
  /** Receives every freshly accepted document (active-editor cache reset). */
  readonly onAccepted?: (document: StudioDocument) => void;
}

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

/**
 * The frontend-driven whole-book generation loop (#318): over the existing
 * synchronous endpoints it drafts a `generate` proposal per planned chapter,
 * auto-accepts it, and refreshes project/jobs state exactly like the manual
 * copilot accept flow. Stop is checked before starting a draft and again
 * before accepting one — once requested, no further chapter starts and no
 * further manuscript change lands; an in-flight request may still settle but
 * its result is discarded. Because the plan is recomputed from persisted
 * documents at every start, resume simply begins at the first chapter whose
 * current revision is not `ai-accepted`.
 */
export function useWholeBookLoop({
  projectId,
  provider,
  setProject,
  loadJobs,
  onAccepted,
}: UseWholeBookLoopArgs) {
  const [phase, setPhase] = useState<WholeBookPhase>({ kind: 'idle' });
  const runningRef = useRef(false);
  const stopRequestedRef = useRef(false);

  const stop = useCallback(() => {
    stopRequestedRef.current = true;
  }, []);

  const start = useCallback(
    (plan: WholeBookChapter[]): Promise<void> => {
      if (runningRef.current) return Promise.resolve();
      runningRef.current = true;
      stopRequestedRef.current = false;
      setPhase({ kind: 'running', current: 1, total: plan.length });

      const run = async (): Promise<void> => {
        let generated = 0;
        let failingTitle = plan[0]?.title ?? '';
        try {
          for (let index = 0; index < plan.length; index += 1) {
            if (stopRequestedRef.current) break;
            const chapter = plan[index];
            failingTitle = chapter.title;
            setPhase({ kind: 'running', current: index + 1, total: plan.length });
            // Sequential by design (#318): every draft depends on the previous
            // accept having landed, and stop/progress semantics keep exactly
            // one chapter in flight.
            // react-doctor-disable-next-line async-await-in-loop
            const job = await api.proposal(projectId, chapter.id, 'generate', '', provider);
            if (stopRequestedRef.current) break;
            await api.acceptProposal(projectId, job.id);
            generated += 1;
            const refreshed = await api.project(projectId);
            setProject(refreshed);
            const acceptedDocument = refreshed.documents?.find(
              (document) => document.id === chapter.id,
            );
            if (acceptedDocument) onAccepted?.(acceptedDocument);
            loadJobs();
          }
          if (stopRequestedRef.current) {
            setPhase({ kind: 'done', generated, stoppedEarly: true });
          } else {
            setPhase({ kind: 'done', generated, stoppedEarly: false });
          }
        } catch (reason) {
          // A stop racing an error still reports the stop, not the noise.
          if (stopRequestedRef.current) {
            setPhase({ kind: 'done', generated, stoppedEarly: true });
          } else {
            setPhase({
              kind: 'failed',
              generated,
              failedChapterTitle: failingTitle,
              message: errorMessage(reason, 'Unable to generate the chapter.'),
            });
          }
        } finally {
          runningRef.current = false;
          stopRequestedRef.current = false;
        }
      };

      return run();
    },
    [loadJobs, onAccepted, projectId, provider, setProject],
  );

  return { phase, start, stop };
}
