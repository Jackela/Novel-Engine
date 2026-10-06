import { type RefObject, useCallback, useState } from "react";

import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";

import { toErrorMessage } from "./toErrorMessage";

/** The inline failure a row's confirmation strip renders (#DR-018). */
interface ProjectDeletionFailure {
  readonly projectId: string;
  readonly message: string;
}

interface UseProjectLibraryDeletionOptions {
  /** Re-reads the catalog after a successful removal. */
  readonly reload: () => Promise<void>;
  readonly isMounted: RefObject<boolean>;
  /** Claims the library's single-command slot for one deletion. */
  readonly beginDelete: () => boolean;
  readonly finishDelete: () => void;
}

/**
 * Project-library deletion (#DR-018): one irreversible, single-flight
 * catalog command behind an inline per-row confirmation. A confirmed
 * removal calls `api.deleteProject`, re-reads the catalog, and publishes a
 * live status naming the deleted project; refusals stay on the initiating
 * row until the author cancels. The confirmation warning itself is owned by
 * the row component so Escape/focus behavior stays next to its trigger.
 */
export function useProjectLibraryDeletion({
  reload,
  isMounted,
  beginDelete,
  finishDelete,
}: UseProjectLibraryDeletionOptions) {
  const [confirmingProjectId, setConfirmingProjectId] = useState<string | null>(null);
  const [deletingProjectId, setDeletingProjectId] = useState<string | null>(null);
  const [failure, setFailure] = useState<ProjectDeletionFailure | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const deleteProject = useCallback(
    async (projectId: string, title: string) => {
      if (!beginDelete()) return;
      setDeletingProjectId(projectId);
      setFailure(null);
      setNotice(null);
      try {
        await api.deleteProject(projectId);
        if (!isMounted.current) return;
        setConfirmingProjectId(null);
        setNotice(translateActive("library.status.deleted", { title }));
        await reload();
      } catch (reason) {
        if (isMounted.current) {
          setFailure({
            projectId,
            message: toErrorMessage(reason, translateActive("library.error.unableToDelete")),
          });
        }
      } finally {
        // Single-flight: no newer invocation can hold the command slot, so
        // the busy identity releases unconditionally; publications above
        // stay mount-guarded.
        finishDelete();
        if (isMounted.current) {
          setDeletingProjectId((current) => (current === projectId ? null : current));
        }
      }
    },
    [beginDelete, finishDelete, isMounted, reload],
  );

  const deleteErrorFor = useCallback(
    (projectId: string): string | null =>
      failure?.projectId === projectId ? failure.message : null,
    [failure],
  );

  return {
    confirmingProjectId,
    deletingProjectId,
    deletionNotice: notice,
    setConfirmingProjectId,
    deleteProject,
    deleteErrorFor,
  };
}
