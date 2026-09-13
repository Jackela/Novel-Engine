import { ChevronDown, Loader2, Plus } from "lucide-react";
import { type ComponentProps, type FormEvent, useState } from "react";

import type { DocumentKind, Project } from "@/app/types/studio";
import {
  type PendingDocumentMove,
  StudioNavigatorDocumentRows,
} from "./components/StudioNavigatorDocumentRows";
import type { NavigatorRowCommands } from "./components/StudioNavigatorRowActions";
import { StudioNavigatorSearch } from "./components/StudioNavigatorSearch";
import { StudioWholeBookControl } from "./components/StudioWholeBookControl";
import { useCommandFocusRestoration } from "./hooks/useCommandFocusRestoration";
import { GROUPS, SECTIONS } from "./studioConstants";

interface StudioNavigatorProps {
  project: Project;
  section: string;
  activeId: string | null;
  search: string;
  isSearching: boolean;
  searchResults: ComponentProps<typeof StudioNavigatorSearch>["searchResults"];
  onSearchChange: (value: string) => void;
  onSearchSubmit: (event: FormEvent) => void;
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
  wholeBook?: ComponentProps<typeof StudioWholeBookControl>;
}

export function StudioNavigator({
  project,
  section,
  activeId,
  search,
  isSearching,
  searchResults,
  onSearchChange,
  onSearchSubmit,
  onNavigateSection,
  onSelectDocument,
  onCreateDocument,
  onMoveDocument,
  isCreatingDocument = false,
  isMovingDocument = false,
  creatingDocumentKind = null,
  movingDocument = null,
  rowCommands = null,
  wholeBook,
}: StudioNavigatorProps) {
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);
  const createGroupBusy = isCreatingDocument || creatingDocumentKind !== null;
  const rowCommandsBusy =
    rowCommands !== null &&
    (rowCommands.deletingDocument !== null || rowCommands.placingDocument !== null);
  const documentMutationBusy =
    createGroupBusy || isMovingDocument || movingDocument !== null || rowCommandsBusy;
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
          <span>Project navigation</span>
          <ChevronDown aria-hidden="true" />
        </summary>
        <div className="studio-nav__content">
          <nav className="studio-nav__sections" aria-label="Project sections">
            {SECTIONS.map(([path, label]) => (
              <button
                aria-current={section === path ? "page" : undefined}
                className={
                  section === path
                    ? "studio-nav__section studio-nav__section--active"
                    : "studio-nav__section"
                }
                key={path}
                onClick={() => onNavigateSection(path)}
                type="button"
              >
                {label}
              </button>
            ))}
          </nav>
          <StudioNavigatorSearch
            isSearching={isSearching}
            onSearchChange={onSearchChange}
            onSearchSubmit={onSearchSubmit}
            onSelectDocument={onSelectDocument}
            search={search}
            searchResults={searchResults}
          />
          {showWholeBook ? <StudioWholeBookControl {...wholeBook} /> : null}
          <div className="studio-nav__tree">
            {visibleGroups.map(({ kind, label, icon: Icon }) => {
              const isCreatingThisKind = creatingDocumentKind === kind;
              const documents =
                project.documents?.filter((document) => document.kind === kind) ?? [];
              const volumes = kind === "chapter" ? (project.volumes ?? null) : null;
              const inVolume = (volumeId: string | undefined) =>
                documents.filter(
                  (document) => (document.volume_id ?? volumes?.[0]?.id) === volumeId,
                );
              return (
                <section className="studio-nav__document-group" key={kind}>
                  <header>
                    <span>
                      <Icon aria-hidden="true" /> {label}
                    </span>
                    <button
                      aria-busy={isCreatingThisKind || undefined}
                      aria-label={isCreatingThisKind ? `Adding ${label}` : `Add ${label}`}
                      disabled={documentMutationBusy}
                      onClick={(event) => {
                        void runCreateWithFocusRestoration(event.currentTarget, () =>
                          onCreateDocument(kind),
                        );
                      }}
                      title={isCreatingThisKind ? `Adding ${label}` : `Add ${label}`}
                      type="button"
                    >
                      {isCreatingThisKind ? (
                        <Loader2 aria-hidden="true" className="ui-spin" />
                      ) : (
                        <Plus aria-hidden="true" />
                      )}
                    </button>
                  </header>
                  {volumes && volumes.length > 0 ? (
                    volumes.map((volume) => (
                      <div className="volume-group" key={volume.id}>
                        <p className="studio-nav__volume-header">{volume.title}</p>
                        <StudioNavigatorDocumentRows
                          rows={inVolume(volume.id)}
                          volumes={volumes}
                          {...rowProps}
                        />
                      </div>
                    ))
                  ) : (
                    <StudioNavigatorDocumentRows rows={documents} volumes={volumes} {...rowProps} />
                  )}
                </section>
              );
            })}
          </div>
        </div>
      </details>
    </aside>
  );
}
