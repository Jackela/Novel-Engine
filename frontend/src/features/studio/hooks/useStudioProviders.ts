import { useEffect, useState } from "react";

import { api, HttpError } from "@/app/api";
import type { ProviderInfo } from "@/app/types/studio";

import { DEFAULT_PROVIDER_OPTIONS } from "../studioConstants";
import { reportUnexpectedError } from "./reportUnexpectedError";

/**
 * The fallback catalog is a deliberate degradation for the two failures the
 * transport layer owns: the server's error envelope (`HttpError`) and a
 * browser transport failure (the `TypeError`-caused error
 * `app/networkError.ts` builds, which the offline banner already announces).
 * Any other rejection is a defect — a contract-shape or programming failure —
 * and reaches the diagnostics channel instead of vanishing.
 */
function isExpectedProviderReadFailure(reason: unknown): boolean {
  return (
    reason instanceof HttpError || (reason instanceof Error && reason.cause instanceof TypeError)
  );
}

/**
 * The project-independent provider catalog. The built-in fallback options are
 * returned until the server's catalog arrives, and they stay in place when the
 * read fails, so the settings surface remains usable either way.
 *
 * Failure semantics: an expected read failure degrades silently to the
 * fallback catalog; an unexpected one (a contract or programming failure) is
 * reported through `reportUnexpectedError` while the fallback stays applied,
 * so a broken catalog never renders as an empty provider list.
 */
export function useStudioProviders(): ProviderInfo[] {
  const [providers, setProviders] = useState<ProviderInfo[]>(DEFAULT_PROVIDER_OPTIONS);

  useEffect(() => {
    let cancelled = false;
    api
      .providers()
      .then((response) => {
        if (cancelled || response.providers.length === 0) return;
        setProviders(response.providers);
      })
      .catch((reason: unknown) => {
        // Keep fallback providers on failure so the UI remains usable.
        if (!isExpectedProviderReadFailure(reason)) {
          reportUnexpectedError("Unexpected provider-catalog read failure.", reason);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return providers;
}
