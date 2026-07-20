import { useCallback, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { api } from '@/app/api';
import type { ExportFormat, Project, StudioExport } from '@/app/types/studio';

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
        const item = await api.createExport(projectId, format);
        setExports((current) => [item, ...current]);
        const blob = await api.download(item.download_url);
        const blobUrl = URL.createObjectURL(blob);
        const extension = format === 'markdown' ? 'md' : format;
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = `${project.title}.${extension}`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
      } catch (reason) {
        setFailedFormat(format);
        setError(reason instanceof Error ? reason.message : 'Unable to export project.');
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
