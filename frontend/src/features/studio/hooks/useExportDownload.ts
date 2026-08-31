import type { Dispatch, SetStateAction } from "react";
import { useCallback, useLayoutEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import type { ExportFormat, Project, StudioExport } from "@/app/types/studio";

import { downloadBrowserBlob } from "./downloadBrowserBlob";
import { toErrorMessage } from "./toErrorMessage";

interface ExportOwner {
  readonly projectId: string;
  readonly objectUrls: Set<string>;
  active: boolean;
}

interface ExportInvocation {
  readonly controller: AbortController;
  readonly epoch: number;
  readonly owner: ExportOwner;
}

interface OwnedFormat {
  readonly epoch: number;
  readonly format: ExportFormat;
  readonly projectId: string;
}

interface FailedExport extends OwnedFormat {
  readonly message: string;
}

export function useExportDownload(
  project: Project | null,
  projectId: string,
  setExports: Dispatch<SetStateAction<StudioExport[]>>,
) {
  const [exporting, setExporting] = useState<OwnedFormat | null>(null);
  const [retrying, setRetrying] = useState<OwnedFormat | null>(null);
  const [failed, setFailed] = useState<FailedExport | null>(null);
  const ownerRef = useRef<ExportOwner | null>(null);
  const activeInvocationRef = useRef<ExportInvocation | null>(null);
  const invocationEpochRef = useRef(0);

  useLayoutEffect(() => {
    const owner: ExportOwner = { projectId, objectUrls: new Set<string>(), active: true };
    ownerRef.current = owner;
    return () => {
      owner.active = false;
      invocationEpochRef.current += 1;
      const activeInvocation = activeInvocationRef.current;
      if (activeInvocation?.owner === owner) {
        activeInvocationRef.current = null;
        activeInvocation.controller.abort();
      }
      for (const objectUrl of owner.objectUrls) URL.revokeObjectURL(objectUrl);
      owner.objectUrls.clear();
      if (ownerRef.current === owner) ownerRef.current = null;
    };
  }, [projectId]);

  const isCurrentEpoch = useCallback(
    (invocation: ExportInvocation): boolean =>
      invocation.owner.active &&
      ownerRef.current === invocation.owner &&
      invocationEpochRef.current === invocation.epoch &&
      !invocation.controller.signal.aborted,
    [],
  );

  const isCurrentInvocation = useCallback(
    (invocation: ExportInvocation): boolean =>
      activeInvocationRef.current === invocation && isCurrentEpoch(invocation),
    [isCurrentEpoch],
  );

  const startExport = useCallback(
    async (format: ExportFormat, isRetry: boolean) => {
      const owner = ownerRef.current;
      if (
        !project ||
        project.id !== projectId ||
        !owner?.active ||
        owner.projectId !== projectId ||
        activeInvocationRef.current !== null
      ) {
        return;
      }
      const invocation: ExportInvocation = {
        controller: new AbortController(),
        epoch: invocationEpochRef.current + 1,
        owner,
      };
      invocationEpochRef.current = invocation.epoch;
      activeInvocationRef.current = invocation;
      const ownedFormat: OwnedFormat = {
        projectId: owner.projectId,
        epoch: invocation.epoch,
        format,
      };
      setExporting(ownedFormat);
      setRetrying(isRetry ? ownedFormat : null);
      if (isRetry) {
        setFailed((current) =>
          current?.projectId === owner.projectId
            ? { ...ownedFormat, message: current.message }
            : current,
        );
      } else {
        setFailed(null);
      }
      let completed = false;
      try {
        // The synchronous job contract (#272): the response is the terminal
        // export job; the artifact catalog is refreshed from its export_id.
        const requestInit = { signal: invocation.controller.signal };
        const job = await api.createExport(owner.projectId, format, requestInit);
        if (!isCurrentInvocation(invocation)) return;
        if (job.status !== "completed" || !job.result.export_id) {
          throw new Error(job.error ?? "Unable to export project.");
        }
        const catalog = await api.exports(owner.projectId, requestInit);
        if (!isCurrentInvocation(invocation)) return;
        setExports((current) => (isCurrentEpoch(invocation) ? catalog.exports : current));
        const item = catalog.exports.find((candidate) => candidate.id === job.result.export_id);
        if (!item) {
          throw new Error("Export artifact is not available.");
        }
        const blob = await api.download(item.download_url, requestInit);
        if (!isCurrentInvocation(invocation)) return;
        const extension = format === "markdown" ? "md" : format;
        await downloadBrowserBlob({
          activeObjectUrls: owner.objectUrls,
          blob,
          filename: `${project.title}.${extension}`,
          shouldDownload: () => isCurrentInvocation(invocation),
        });
        completed = true;
      } catch (reason) {
        if (!isCurrentInvocation(invocation)) return;
        setFailed({
          ...ownedFormat,
          message: toErrorMessage(reason, "Unable to export project."),
        });
      } finally {
        if (isCurrentInvocation(invocation)) {
          setExporting((current) =>
            isCurrentEpoch(invocation) && current?.epoch === invocation.epoch ? null : current,
          );
          setRetrying((current) =>
            isCurrentEpoch(invocation) && current?.epoch === invocation.epoch ? null : current,
          );
          if (completed) {
            setFailed((current) =>
              isCurrentEpoch(invocation) && current?.epoch === invocation.epoch ? null : current,
            );
          }
        }
        if (activeInvocationRef.current === invocation) activeInvocationRef.current = null;
      }
    },
    [isCurrentEpoch, isCurrentInvocation, project, projectId, setExports],
  );

  const exportProject = useCallback(
    (format: ExportFormat) => startExport(format, false),
    [startExport],
  );
  const retryExport = useCallback(
    (format: ExportFormat) => startExport(format, true),
    [startExport],
  );

  const exportingFormat =
    exporting?.projectId === projectId && exporting.epoch === invocationEpochRef.current
      ? exporting.format
      : null;
  const failedFormat =
    failed?.projectId === projectId && failed.epoch === invocationEpochRef.current
      ? failed.format
      : null;
  const exportError =
    failed?.projectId === projectId && failed.epoch === invocationEpochRef.current
      ? failed.message
      : null;
  const retryingFormat =
    retrying?.projectId === projectId && retrying.epoch === invocationEpochRef.current
      ? retrying.format
      : null;

  return {
    exportProject,
    retryExport,
    exportingFormat,
    retryingFormat,
    failedFormat,
    exportError,
  };
}
