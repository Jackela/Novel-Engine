import { ChevronDown } from "lucide-react";
import { type ComponentProps, type FormEvent, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { DocumentKind, Project } from "@/app/types/studio";
import { StudioNavigatorDocumentGroup } from "./components/StudioNavigatorDocumentGroup";
import type { PendingDocumentMove } from "./components/StudioNavigatorDocumentRows";
import type { NavigatorRowCommands } from "./components/StudioNavigatorRowActions";
import { StudioNavigatorSearch } from "./components/StudioNavigatorSearch";
import { StudioNavigatorSections } from "./components/StudioNavigatorSections";
import type { NavigatorVolumeCommands } from "./components/StudioNavigatorVolumeHeader";
import { StudioWholeBookControl } from "./components/StudioWholeBookControl";
import { useCommandFocusRestoration } from "./hooks/useCommandFocusRestoration";
import { GROUPS } from "./studioConstants";

interface StudioNavigatorProps {
  project: Project;
  section: string;
  activeId: string | null;
  search: string;
  isSearching: boolean;
  searchResults: ComponentProps<typeof StudioNavigatorSearch>["searchResults"];
  /** Honest project-wide match count of the shown query (DR-029). */
  searchTotal?: number;
  /** DR-029 paging/empty flags as one object: keeps the boolean-prop count down. */
  searchState?: NavigatorSearchState;
  onSearchChange: (value: string) => void;
  onSearchSubmit: (event: FormEvent) => void;
  /** DR-029: opens the document and locates the hit; rows use onSelectDocument. */
  onSelectResult?: (result: NavigatorSearchResult) => void;
  onLoadMore?: () => void;
  onNavigateSection: (section: string) => void;
  onSelectDocument: (documentId: string) => void;
  onCreateDocument: (kind: DocumentKind) => void | Promise<void>;
  onMoveDocument: (documentId: string, direction: -1 | 1) => void | Promise<void>;
  isCreatingDocument?: boolean;
  isMovingDocument?: boolean;
  creatingDocumentKind?: DocumentKind | null;
  movingDocument?: PendingDocumentMove | null;
  /** Per-row delete/placement commands (#481); absent renders neither. */
  rowCommands?: NavigatorRowCommands | null;
  /** Volume management (DR-017); absent renders titles without controls. */
  volumeCommands?: NavigatorVolumeCommands | null;
  wholeBook?: ComponentProps<typeof StudioWholeBookControl>;
}

/** One ranked search hit as the navigator renders it (DR-029). */
export type NavigatorSearchResult = ComponentProps<
  typeof StudioNavigatorSearch
>["searchResults"][number];

/** DR-029 paging/empty flags of the search surface, grouped as one prop. */
export interface NavigatorSearchState {
  readonly hasMoreResults: boolean;
  readonly isLoadingMore: boolean;
  readonly searchedEmpty: boolean;
}

export function StudioNavigator({
  project,
  section,
  activeId,
  search,
  isSearching,
  searchResults,
  searchTotal = 0,
  searchState = { hasMoreResults: false, isLoadingMore: false, searchedEmpty: false },
  onSearchChange,
  onSearchSubmit,
  onSelectResult,
  onLoadMore = () => undefined,
  onNavigateSection,
  onSelectDocument,
  onCreateDocument,
  onMoveDocument,
  isCreatingDocument = false,
  isMovingDocument = false,
  creatingDocumentKind = null,
  movingDocument = null,
  rowCommands = null,
  volumeCommands = null,
  wholeBook,
}: StudioNavigatorProps) {
  const { t } = useTranslation();
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);
  const createGroupBusy = isCreatingDocument || creatingDocumentKind !== null;
  const rowCommandsBusy =
    rowCommands !== null &&
    (rowCommands.deletingDocument !== null || rowCommands.placingDocument !== null);
  const volumeCommandsBusy =
    volumeCommands !== null &&
    (volumeCommands.isCreatingVolume ||
      volumeCommands.renamingVolume !== null ||
      volumeCommands.deletingVolume !== null ||
      volumeCommands.movingVolume !== null);
  const documentMutationBusy =
    createGroupBusy ||
    isMovingDocument ||
    movingDocument !== null ||
    rowCommandsBusy ||
    volumeCommandsBusy;
  const runCreateWithFocusRestoration = useCommandFocusRestoration(documentMutationBusy);
  const showWholeBook =
    wholeBook !== undefined && (section === "manuscript" || wholeBook.phase.kind !== "idle");
  const visibleGroups = GROUPS.flatMap((group) => {
    if (section === "outline" && group.kind !== "outline") return [];
    if (section === "characters" && group.kind !== "character") return [];
    if (section === "world" && group.kind !== "world") return [];
    return [group];
  });

  const rowProps = {
    activeId,
    isMovingDocument: documentMutationBusy,
    movingDocument,
    onSelectDocument,
    onMoveDocument,
    rowCommands,
    confirmingDeleteId,
    onConfirmingDeleteChange: setConfirmingDeleteId,
  };

  return (
    <aside className="studio-nav">
      <details className="studio-nav__disclosure" open>
        <summary className="studio-nav__summary">
          <span>{t("navigator.disclosure")}</span>
          <ChevronDown aria-hidden="true" />
        </summary>
        <div className="studio-nav__content">
          <StudioNavigatorSections onNavigateSection={onNavigateSection} section={section} />
          <StudioNavigatorSearch
            hasMoreResults={searchState.hasMoreResults}
            isLoadingMore={searchState.isLoadingMore}
            isSearching={isSearching}
            onLoadMore={onLoadMore}
            onSearchChange={onSearchChange}
            onSearchSubmit={onSearchSubmit}
            onSelectResult={onSelectResult ?? ((result) => onSelectDocument(result.document_id))}
            search={search}
            searchResults={searchResults}
            searchTotal={searchTotal}
            searchedEmpty={searchState.searchedEmpty}
          />
          {showWholeBook ? <StudioWholeBookControl {...wholeBook} /> : null}
          <div className="studio-nav__tree">
            {visibleGroups.map((group) => (
              <StudioNavigatorDocumentGroup
                key={group.kind}
                creatingDocumentKind={creatingDocumentKind}
                documentMutationBusy={documentMutationBusy}
                group={group}
                onCreateDocument={onCreateDocument}
                project={project}
                rowProps={rowProps}
                runCreateWithFocusRestoration={runCreateWithFocusRestoration}
                volumeCommands={volumeCommands}
              />
            ))}
          </div>
        </div>
      </details>
    </aside>
  );
}
