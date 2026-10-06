import { useCallback, useRef, useState } from "react";

import type { SearchResult, SearchReveal } from "./useStudioSearch";

/**
 * DR-029 page-level "open this hit" intent. Requesting a reveal records the
 * target document, the locate term, and a fresh monotonic token, so the
 * editor re-runs its find even when the same result is clicked twice; the
 * editor only consumes it while the target document is the active one.
 */
export function useSearchReveal(): {
  reveal: SearchReveal | null;
  requestReveal: (result: SearchResult) => void;
} {
  const [reveal, setReveal] = useState<SearchReveal | null>(null);
  const tokenRef = useRef(0);

  const requestReveal = useCallback((result: SearchResult) => {
    tokenRef.current += 1;
    setReveal({
      documentId: result.document_id,
      term: result.match_term,
      token: tokenRef.current,
    });
  }, []);

  return { reveal, requestReveal };
}
