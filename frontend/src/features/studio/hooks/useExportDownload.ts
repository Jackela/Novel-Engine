import type { Dispatch, SetStateAction } from "react";
import { useCallback, useRef, useState } from "react";

import { api } from "@/app/api";
import type { ExportFormat, Project, StudioExport } from "@/app/types/studio";

import { toErrorMessage } from "./toErrorMessage";

export function useExportDownload(
  project: Project | null,
  projectId: string,
  setExports: Dispatch<SetStateAction<StudioExport[]>>,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(null);
  const [failedFormat, setFailedFormat] = useState<ExportFormat | null>(null);
  const exportingRef = useRef(false);

  const exportProject = useCallback(
    async (format: ExportFormat) => {
      if (!project || exportingRef.current) return;
      exportingRef.current = true;
      setExportingFormat(format);
      setFailedFormat(null);
      setError(null);
      try {
        // The synchronous job contract (#272): the response is the terminal
        // export job; the artifact catalog is refreshed from its export_id.
        const job = await api.createExport(projectId, format);
        if (job.status !== "completed" || !job.result.export_id) {
          throw new Error(job.error ?? "Unable to export project.");
        }
        const catalog = await api.exports(projectId);
        setExports(catalog.exports);
        const item = catalog.exports.find((candidate) => candidate.id === job.result.export_id);
        if (!item) {
          throw new Error("Export artifact is not available.");
        }
        const blob = await api.download(item.download_url);
        const blobUrl = URL.createObjectURL(blob);
        const extension = format === "markdown" ? "md" : format;
        const link = document.createElement("a");
        link.href = blobUrl;
        link.download = `${project.title}.${extension}`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
      } catch (reason) {
        setFailedFormat(format);
        setError(toErrorMessage(reason, "Unable to export project."));
      } finally {
        exportingRef.current = false;
        setExportingFormat(null);
      }
    },
    [project, projectId, setExports, setError],
  );

  return {
    exportProject,
    exportingFormat,
    failedFormat,
  };
}
