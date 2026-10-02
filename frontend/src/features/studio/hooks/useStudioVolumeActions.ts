import type { Dispatch, SetStateAction } from "react";
import { useCallback, useState } from "react";

import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import type { Project } from "@/app/types/studio";
import {
  mergeProjectVolume,
  removeProjectVolume,
  replaceProjectVolumes,
  swapVolumeNeighborIds,
} from "./projectState";
import { toErrorMessage } from "./toErrorMessage";
import { usePendingAction } from "./usePendingAction";

const VOLUME_ACTION_KEYS = ["addVolume", "renameVolume", "deleteVolume", "moveVolume"] as const;
type VolumeActionKey = (typeof VOLUME_ACTION_KEYS)[number];

interface VolumeActionsOwner {
  readonly projectId: string;
}

interface ScopedRenamingVolume {
  readonly projectId: string;
  readonly volumeId: string;
}

interface ScopedDeletingVolume {
  readonly projectId: string;
  readonly volumeId: string;
}

interface ScopedMovingVolume {
  readonly projectId: string;
  readonly volumeId: string;
  readonly direction: -1 | 1;
}

/** The inline failure one volume command leaves on its initiating surface. */
interface VolumeFailure {
  readonly key: string;
  readonly message: string;
}

interface UseStudioVolumeActionsOptions<Owner extends VolumeActionsOwner> {
  readonly project: Project | null;
  readonly projectId: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly currentOwner: () => Owner | null;
  readonly isCurrentOwner: (owner: Owner) => boolean;
}

/**
 * Navigator volume management (ADR-0005): create, rename, delete, and
 * whole-set reorder behind one flat command surface. Every success applies
 * exactly the fields its response (or the observed delete contract) owns —
 * no follow-up shell read — while refusals stay on the initiating surface as
 * inline errors, including the server's last-volume guard for deletion. All
 * commands are single-flight per key so double dispatch during the render gap
 * cannot fire twice.
 */
export function useStudioVolumeActions<Owner extends VolumeActionsOwner>({
  project,
  projectId,
  setProject,
  currentOwner,
  isCurrentOwner,
}: UseStudioVolumeActionsOptions<Owner>) {
  const { pending, begin, finish } = usePendingAction<VolumeActionKey>(VOLUME_ACTION_KEYS);
  const [renamingState, setRenamingState] = useState<ScopedRenamingVolume | null>(null);
  const [deletingState, setDeletingState] = useState<ScopedDeletingVolume | null>(null);
  const [movingState, setMovingState] = useState<ScopedMovingVolume | null>(null);
  const [failure, setFailure] = useState<VolumeFailure | null>(null);

  const addVolume = useCallback(
    async (title: string) => {
      const owner = currentOwner();
      if (!owner || !project || !begin("addVolume")) return;
      setFailure(null);
      try {
        const created = await api.createVolume(project.id, title);
        if (!isCurrentOwner(owner)) return;
        setProject((current) =>
          isCurrentOwner(owner) && current?.id === owner.projectId
            ? replaceProjectVolumes(current, [...current.volumes, created])
            : current,
        );
      } catch (reason) {
        if (isCurrentOwner(owner)) {
          setFailure({
            key: `${owner.projectId}:addVolume`,
            message: toErrorMessage(reason, translateActive("errors.createVolume")),
          });
        }
      } finally {
        finish("addVolume");
      }
    },
    [begin, currentOwner, finish, isCurrentOwner, project, setProject],
  );

  const renameVolume = useCallback(
    async (volumeId: string, title: string) => {
      const owner = currentOwner();
      if (!owner || !project || !begin("renameVolume")) return;
      setRenamingState({ projectId: owner.projectId, volumeId });
      setFailure(null);
      try {
        const updated = await api.renameVolume(project.id, volumeId, title);
        if (!isCurrentOwner(owner)) return;
        setProject((current) =>
          isCurrentOwner(owner) && current?.id === owner.projectId
            ? mergeProjectVolume(current, updated)
            : current,
        );
      } catch (reason) {
        if (isCurrentOwner(owner)) {
          setFailure({
            key: `${owner.projectId}:renameVolume:${volumeId}`,
            message: toErrorMessage(reason, translateActive("errors.renameVolume")),
          });
        }
      } finally {
        setRenamingState((current) =>
          current?.projectId === owner.projectId && current.volumeId === volumeId ? null : current,
        );
        finish("renameVolume");
      }
    },
    [begin, currentOwner, finish, isCurrentOwner, project, setProject],
  );

  const deleteVolume = useCallback(
    async (volumeId: string) => {
      const owner = currentOwner();
      if (!owner || !project || !begin("deleteVolume")) return;
      setDeletingState({ projectId: owner.projectId, volumeId });
      setFailure(null);
      try {
        await api.deleteVolume(project.id, volumeId);
        if (!isCurrentOwner(owner)) return;
        setProject((current) =>
          isCurrentOwner(owner) && current?.id === owner.projectId
            ? removeProjectVolume(current, volumeId)
            : current,
        );
      } catch (reason) {
        if (isCurrentOwner(owner)) {
          setFailure({
            key: `${owner.projectId}:deleteVolume:${volumeId}`,
            message: toErrorMessage(reason, translateActive("errors.deleteVolume")),
          });
        }
      } finally {
        setDeletingState((current) =>
          current?.projectId === owner.projectId && current.volumeId === volumeId ? null : current,
        );
        finish("deleteVolume");
      }
    },
    [begin, currentOwner, finish, isCurrentOwner, project, setProject],
  );

  const moveVolume = useCallback(
    async (volumeId: string, direction: -1 | 1) => {
      const owner = currentOwner();
      if (!owner || !project) return;
      const orderedIds = swapVolumeNeighborIds(project.volumes, volumeId, direction);
      if (orderedIds === null || !begin("moveVolume")) return;
      setMovingState({ projectId: owner.projectId, volumeId, direction });
      setFailure(null);
      try {
        const response = await api.reorderVolumes(project.id, orderedIds);
        if (!isCurrentOwner(owner)) return;
        setProject((current) =>
          isCurrentOwner(owner) && current?.id === owner.projectId
            ? replaceProjectVolumes(current, response.volumes)
            : current,
        );
      } catch (reason) {
        if (isCurrentOwner(owner)) {
          setFailure({
            key: `${owner.projectId}:moveVolume:${volumeId}`,
            message: toErrorMessage(reason, translateActive("errors.reorderVolumes")),
          });
        }
      } finally {
        setMovingState((current) =>
          current?.projectId === owner.projectId &&
          current.volumeId === volumeId &&
          current.direction === direction
            ? null
            : current,
        );
        finish("moveVolume");
      }
    },
    [begin, currentOwner, finish, isCurrentOwner, project, setProject],
  );

  const errorFor = useCallback(
    (
      operation: "addVolume" | "renameVolume" | "deleteVolume" | "moveVolume",
      volumeId?: string,
    ) => {
      const key =
        volumeId === undefined
          ? `${projectId}:${operation}`
          : `${projectId}:${operation}:${volumeId}`;
      return failure?.key === key ? failure.message : null;
    },
    [failure, projectId],
  );

  return {
    addVolume,
    renameVolume,
    deleteVolume,
    moveVolume,
    isCreatingVolume: pending.addVolume,
    createVolumeError: errorFor("addVolume"),
    renamingVolume:
      renamingState?.projectId === projectId ? { volumeId: renamingState.volumeId } : null,
    renameErrorFor: (volumeId: string) => errorFor("renameVolume", volumeId),
    deletingVolume:
      deletingState?.projectId === projectId ? { volumeId: deletingState.volumeId } : null,
    deleteErrorFor: (volumeId: string) => errorFor("deleteVolume", volumeId),
    movingVolume:
      movingState?.projectId === projectId
        ? { volumeId: movingState.volumeId, direction: movingState.direction }
        : null,
    moveErrorFor: (volumeId: string) => errorFor("moveVolume", volumeId),
  };
}
