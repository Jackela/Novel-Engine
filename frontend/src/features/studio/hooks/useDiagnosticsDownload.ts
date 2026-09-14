import { useCallback, useLayoutEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import { downloadBrowserBlob } from "./downloadBrowserBlob";
import { toErrorMessage } from "./toErrorMessage";

/**
 * The client-derived diagnostics filename (#654):
 * `novel-engine-diagnostics-<UTC date>.json`, mirroring the export surface's
 * client-derived download names.
 */
export function diagnosticsFileName(now: Date): string {
  return `novel-engine-diagnostics-${now.toISOString().slice(0, 10)}.json`;
}

/**
 * The Settings panel's opt-in diagnostics export (#654). One activation
 * performs exactly one request — to this Studio's own read-only
 * project-scoped diagnostics endpoint — serializes the summary as JSON, and
 * saves it through the browser's download with the client-derived filename.
 * Nothing is uploaded; where the file goes is the author's decision alone.
 */
export function useDiagnosticsDownload(projectId: string) {
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const objectUrlsRef = useRef(new Set<string>());
  const controllerRef = useRef<AbortController | null>(null);
  const inFlightRef = useRef(false);

  useLayoutEffect(() => {
    const objectUrls = objectUrlsRef.current;
    return () => {
      controllerRef.current?.abort();
      controllerRef.current = null;
      for (const objectUrl of objectUrls) URL.revokeObjectURL(objectUrl);
      objectUrls.clear();
      inFlightRef.current = false;
    };
  }, []);

  const exportDiagnostics = useCallback(async () => {
    // Duplicate-submission guard: one export in flight at a time.
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    const controller = new AbortController();
    controllerRef.current = controller;
    setIsExporting(true);
    let completed = false;
    try {
      const summary = await api.diagnostics(projectId, { signal: controller.signal });
      const blob = new Blob([`${JSON.stringify(summary, null, 2)}\n`], {
        type: "application/json",
      });
      await downloadBrowserBlob({
        activeObjectUrls: objectUrlsRef.current,
        blob,
        filename: diagnosticsFileName(new Date()),
        shouldDownload: () => !controller.signal.aborted,
      });
      completed = true;
    } catch (reason) {
      if (controller.signal.aborted) return;
      setError(toErrorMessage(reason, translateActive("errors.exportDiagnostics")));
    } finally {
      if (!controller.signal.aborted) {
        if (completed) setError(null);
        setIsExporting(false);
      }
      if (controllerRef.current === controller) controllerRef.current = null;
      inFlightRef.current = false;
    }
  }, [projectId]);

  return {
    exportDiagnostics,
    isExportingDiagnostics: isExporting,
    diagnosticsError: error,
  };
}
