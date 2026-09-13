import type { RevisionSummary } from "@/app/types/studio";

export type RevisionRequestIntent = "activation" | "refresh" | "older";

export interface QueuedOlderRequest {
  readonly projectId: string;
  readonly documentId: string;
  readonly promise: Promise<void>;
  readonly resolve: () => void;
}

export interface ActiveRevisionRequest {
  readonly intent: RevisionRequestIntent;
  readonly cursor: string | null;
  readonly expectedRevisionId: string | null;
  readonly controller: AbortController;
  readonly version: number;
  readonly olderWaiter: QueuedOlderRequest | null;
  promise: Promise<void>;
}

export interface RevisionSubscriber {
  onError: (reason: unknown) => void;
  onSuccess: () => void;
}

export interface RevisionOwnerState {
  readonly revisions: RevisionSummary[];
  readonly initialized: boolean;
  readonly hasOlder: boolean;
  readonly isLoadingOlder: boolean;
  readonly isLoading: boolean;
}
