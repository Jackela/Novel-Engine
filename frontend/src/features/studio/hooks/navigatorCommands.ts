import type { NavigatorRowCommands } from "../components/StudioNavigatorRowActions";
import type { NavigatorVolumeCommands } from "../components/StudioNavigatorVolumeHeader";

/** The #481 row-command surfaces `useStudioActions` exposes for the Navigator. */
interface RowCommandActions {
  readonly deleteDocument: (documentId: string) => void | Promise<void>;
  readonly placeChapter: (documentId: string, volumeId: string) => void | Promise<void>;
  readonly deletingDocument: { readonly documentId: string } | null;
  readonly placingDocument: { readonly documentId: string; readonly volumeId: string } | null;
  readonly deletionFor: (documentId: string) => { readonly error: string | null };
  readonly placementFor: (documentId: string) => { readonly error: string | null };
}

/** The volume-management surfaces `useStudioActions` exposes for the Navigator. */
interface VolumeCommandActions {
  readonly addVolume: (title: string) => void | Promise<void>;
  readonly renameVolume: (volumeId: string, title: string) => void | Promise<void>;
  readonly deleteVolume: (volumeId: string) => void | Promise<void>;
  readonly moveVolume: (volumeId: string, direction: -1 | 1) => void | Promise<void>;
  readonly isCreatingVolume: boolean;
  readonly createVolumeError: string | null;
  readonly renamingVolume: { readonly volumeId: string } | null;
  readonly renameErrorFor: (volumeId: string) => string | null;
  readonly deletingVolume: { readonly volumeId: string } | null;
  readonly deleteErrorFor: (volumeId: string) => string | null;
  readonly movingVolume: { readonly volumeId: string; readonly direction: -1 | 1 } | null;
  readonly moveErrorFor: (volumeId: string) => string | null;
}

type NavigatorCommandActions = RowCommandActions & VolumeCommandActions;

/**
 * Adapt the deletion/placement (#481) and volume-management (DR-017) command
 * hooks into the Navigator's `rowCommands`/`volumeCommands` models: exact
 * pending identities plus per-row/per-volume inline errors, including the
 * server's last-volume delete refusal.
 */
export function buildNavigatorCommands(actions: NavigatorCommandActions): {
  readonly rowCommands: NavigatorRowCommands;
  readonly volumeCommands: NavigatorVolumeCommands;
} {
  return {
    rowCommands: {
      onDeleteDocument: actions.deleteDocument,
      onPlaceChapter: actions.placeChapter,
      deletingDocument: actions.deletingDocument,
      placingDocument: actions.placingDocument,
      deletionErrorFor: (documentId) => actions.deletionFor(documentId).error,
      placementErrorFor: (documentId) => actions.placementFor(documentId).error,
    },
    volumeCommands: {
      onAddVolume: actions.addVolume,
      onRenameVolume: actions.renameVolume,
      onDeleteVolume: actions.deleteVolume,
      onMoveVolume: actions.moveVolume,
      isCreatingVolume: actions.isCreatingVolume,
      createError: actions.createVolumeError,
      renamingVolume: actions.renamingVolume,
      renameErrorFor: actions.renameErrorFor,
      deletingVolume: actions.deletingVolume,
      deleteErrorFor: actions.deleteErrorFor,
      movingVolume: actions.movingVolume,
      moveErrorFor: actions.moveErrorFor,
    },
  };
}
