import { api } from "@/app/api";
import type { StudioDocument } from "@/app/types/studio";

export interface CurrentDocumentReadKey {
  readonly projectId: string;
  readonly documentId: string;
  readonly expectedRevisionId: string;
  readonly lifecycle: symbol;
}

interface SharedRead {
  readonly key: CurrentDocumentReadKey;
  readonly controller: AbortController;
  readonly promise: Promise<StudioDocument>;
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
  readonly promise: Promise<StudioDocument>;
  release: () => void;
}

/** Coalesces only an exact causal owner tuple; it never caches successful bodies. */
export function acquireCurrentDocumentRead(key: CurrentDocumentReadKey): CurrentDocumentReadLease {
  let read = findRead(key);
  if (!read) {
    const controller = new AbortController();
    read = {
      key,
      controller,
      promise: api.document(key.projectId, key.documentId, { signal: controller.signal }),
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
