import { Loader2, Plus } from "lucide-react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { DocumentKind, Project } from "@/app/types/studio";

import type { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import type { GROUPS } from "../studioConstants";
import {
  type PendingDocumentMove,
  StudioNavigatorDocumentRows,
} from "./StudioNavigatorDocumentRows";
import type { NavigatorRowCommands } from "./StudioNavigatorRowActions";
import { StudioNavigatorVolumeCreate } from "./StudioNavigatorVolumeCreate";
import type { NavigatorVolumeCommands } from "./StudioNavigatorVolumeHeader";
import { StudioNavigatorVolumeList } from "./StudioNavigatorVolumeList";

/** One document group descriptor from the navigator's group table. */
type NavigatorGroup = (typeof GROUPS)[number];

/** The row props every document row of the group shares. */
interface StudioNavigatorGroupRowProps {
  readonly activeId: string | null;
  readonly isMovingDocument: boolean;
  readonly movingDocument: PendingDocumentMove | null;
  readonly onSelectDocument: (documentId: string) => void;
  readonly onMoveDocument: (documentId: string, direction: -1 | 1) => void | Promise<void>;
  /** Per-row delete/placement commands (#481); absent renders neither. */
  readonly rowCommands?: NavigatorRowCommands | null;
  readonly confirmingDeleteId: string | null;
  readonly onConfirmingDeleteChange: (documentId: string | null) => void;
}

interface StudioNavigatorDocumentGroupProps {
  readonly group: NavigatorGroup;
  readonly project: Project;
  /** The document kind whose create command is in flight. */
  readonly creatingDocumentKind: DocumentKind | null;
  /** True while any document mutation (create/move/row/volume) owns the navigator. */
  readonly documentMutationBusy: boolean;
  /** Volume management (DR-017); absent renders titles without controls. */
  readonly volumeCommands: NavigatorVolumeCommands | null;
  readonly onCreateDocument: (kind: DocumentKind) => void | Promise<void>;
  readonly runCreateWithFocusRestoration: ReturnType<typeof useCommandFocusRestoration>;
  readonly rowProps: StudioNavigatorGroupRowProps;
}

/**
 * One document group (manuscript chapters, outline, characters,
 * world, notes): its header with the Add command, the DR-017
 * volume tools when the group is chapters, and the group's rows —
 * under volume headers in reading order when volumes exist, flat
 * otherwise. A chapter without a volume_id lands in the first
 * volume's rows.
 */
export function StudioNavigatorDocumentGroup({
  creatingDocumentKind,
  documentMutationBusy,
  group,
  onCreateDocument,
  project,
  rowProps,
  runCreateWithFocusRestoration,
  volumeCommands,
}: StudioNavigatorDocumentGroupProps) {
  const { t } = useTranslation();
  const { kind, messageKey, icon: Icon } = group;
  const isCreatingThisKind = creatingDocumentKind === kind;
  const documents = project.documents?.filter((document) => document.kind === kind) ?? [];
  const volumes = kind === "chapter" ? (project.volumes ?? null) : null;
  const inVolume = (volumeId: string | undefined) =>
    documents.filter((document) => (document.volume_id ?? volumes?.[0]?.id) === volumeId);
  return (
    <section className="studio-nav__document-group">
      <header>
        <span>
          <Icon aria-hidden="true" /> {t(messageKey)}
        </span>
        <button
          aria-busy={isCreatingThisKind || undefined}
          aria-label={
            isCreatingThisKind
              ? t("navigator.group.adding", { group: t(messageKey) })
              : t("navigator.group.add", { group: t(messageKey) })
          }
          disabled={documentMutationBusy}
          onClick={(event) => {
            void runCreateWithFocusRestoration(event.currentTarget, () => onCreateDocument(kind));
          }}
          title={
            isCreatingThisKind
              ? t("navigator.group.adding", { group: t(messageKey) })
              : t("navigator.group.add", { group: t(messageKey) })
          }
          type="button"
        >
          {isCreatingThisKind ? (
            <Loader2 aria-hidden="true" className="ui-spin" />
          ) : (
            <Plus aria-hidden="true" />
          )}
        </button>
      </header>
      {kind === "chapter" && volumeCommands !== null ? (
        <StudioNavigatorVolumeCreate
          commands={volumeCommands}
          isMutationBusy={documentMutationBusy}
        />
      ) : null}
      {volumes && volumes.length > 0 ? (
        <StudioNavigatorVolumeList
          commands={volumeCommands}
          isMutationBusy={documentMutationBusy}
          renderRows={(volume) => (
            <StudioNavigatorDocumentRows
              rows={inVolume(volume.id)}
              volumes={volumes}
              {...rowProps}
            />
          )}
          volumes={volumes}
        />
      ) : (
        <StudioNavigatorDocumentRows rows={documents} volumes={volumes} {...rowProps} />
      )}
    </section>
  );
}
