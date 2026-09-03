import type { CurrentDocumentReadOutcome } from "./currentDocumentReadCycle";

export interface CurrentDocumentReadKey {
  readonly projectId: string;
  readonly documentId: string;
  readonly expectedRevisionId: string;
  readonly lifecycle: symbol;
}

interface SharedRead {
  readonly key: CurrentDocumentReadKey;
  readonly controller: AbortController;
  readonly promise: Promise<CurrentDocumentReadOutcome>;
  subscribers: number;
  settled: boolean;
}

const reads = new Set<SharedRead>();

function sameKey(left: CurrentDocumentReadKey, right: CurrentDocumentReadKey): boolean {
  return (
    left.projectId === right.projectId &&
    left.documentId === right.documentId &&
    left.expectedRevisionId === right.expectedRevisionId &&
    left.lifecycle === right.lifecycle
  );
}

function findRead(key: CurrentDocumentReadKey): SharedRead | undefined {
  for (const read of reads) {
    if (!read.settled && !read.controller.signal.aborted && sameKey(read.key, key)) return read;
  }
  return undefined;
}

export interface CurrentDocumentReadLease {
  readonly promise: Promise<CurrentDocumentReadOutcome>;
  release: () => void;
}

type StartRead = (signal: AbortSignal) => Promise<CurrentDocumentReadOutcome>;

/** Coalesces the complete convergence cycle for one exact causal owner tuple. */
export function acquireCurrentDocumentRead(
  key: CurrentDocumentReadKey,
  start: StartRead,
): CurrentDocumentReadLease {
  let read = findRead(key);
  if (!read) {
    const controller = new AbortController();
    read = {
      key,
      controller,
      promise: start(controller.signal),
      subscribers: 0,
      settled: false,
    };
    reads.add(read);
    const createdRead = read;
    void createdRead.promise.then(
      () => {
        createdRead.settled = true;
        reads.delete(createdRead);
      },
      () => {
        createdRead.settled = true;
        reads.delete(createdRead);
      },
    );
  }
  const activeRead = read;
  activeRead.subscribers += 1;
  let released = false;
  return {
    promise: activeRead.promise,
    release: () => {
      if (released) return;
      released = true;
      activeRead.subscribers -= 1;
      if (activeRead.subscribers === 0 && !activeRead.settled) {
        activeRead.controller.abort();
        reads.delete(activeRead);
      }
    },
  };
}
