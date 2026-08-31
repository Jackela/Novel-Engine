# Studio workspace

The Studio workspace is the project editor at `/projects/:projectId/:section?`. The optional section defaults to `manuscript`; valid path sections are `manuscript`, `outline`, `characters`, `world`, `review`, `history`, `export`, and `settings`. The root route is the entry page, `/projects` is the project library, and an unknown Studio section is canonicalized to the project's manuscript route. `StudioPage` validates the route and keys the complete workbench by `projectId`; `useStudioPageModel` then loads and connects the project aggregate, active document, navigation, editor, Inspector, top bar, and status bar.

Route names and inspector surfaces are not one-to-one. The current mapping is:

| Route section | Primary surface | Behavior |
| --- | --- | --- |
| `manuscript`, `outline`, `characters`, `world` | Editor + selectable Inspector | Copilot is the query-free default. Jobs and Usage are represented by `?inspector=jobs` and `?inspector=usage`. |
| `review` | Review panel | Review is forced active and shows the latest snapshot-bound findings plus the run action. |
| `history` | History panel | Only immutable revision history and restore actions are shown. Export records are not mixed into this panel. |
| `export` | Export panel | Markdown, DOCX, and EPUB actions, pending/error state, and recent export links are shown. Export is not a History alias. |
| `settings` | Settings panel | Project settings render directly without the Inspector tablist. |

The URL is the only owner of the visible Inspector selection. Review, History, and Export use their project paths; Copilot, Jobs, and Usage use the authoring path and validated query value above. Selecting a local panel while on a route-owned panel returns to `manuscript`; an unknown Inspector query fails closed to query-free Copilot. Click, ArrowLeft/ArrowRight, Home, and End activation all navigate through the same route callback, so direct links, refresh, Back, and Forward reconstruct the same selected tab and panel. The top bar contains project identity and back navigation only. Review, Export, and Settings are route-driven and are not duplicated in a second top-bar menu.

**Primary sources:** `frontend/src/app/router.tsx`, `frontend/src/features/studio/StudioPage.tsx`, `frontend/src/features/studio/studioRouteState.ts`.

## Workspace state and hooks

`useStudioProject(projectId)` loads the project, reviews, and exports concurrently as one project-scoped aggregate. A `401` replaces the route with `/`, and a `404` replaces it with `/projects`. Network, timeout, and server failures retain the requested Studio URL and render a readable error with **Try again** and **Back to projects** actions. Retry starts a fresh complete aggregate request; a successful retry clears the stale load error before publishing the requested project. `useActiveDocument` selects an explicitly selected document when it fits the current outline/characters/world section; otherwise it selects the first document of that section. For other sections, it uses the selected document or the first document.

`useStudioInspectorState` is controlled by the validated route state; selecting Jobs also loads its project-scoped job list. `useStudioActions` owns document creation and reordering, review creation, project-settings updates, and job retry. `useStudioProposal`, `useExportDownload`, and `useStudioJobs` own their request state and guards. Workflow hooks report operational errors through the shared Inspector error area, while initial aggregate-load failures use the classified recovery surface above.

The keyed workbench makes the route `projectId` the lifecycle boundary: a project switch unmounts the previous project-local state before the next aggregate becomes interactive. Hooks also capture a project/document owner plus a request epoch and abort transports that accept a signal. Stale reads are discarded. Writes are reconciled differently because cancelling a transport cannot undo a server commit: a project-level guard may refresh the originating aggregate, while a document-level guard prevents that completion from replacing the active editor. Per-document draft state retains unsaved text and its revision base across document navigation; a committed inactive-document update advances its own cached baseline, or keeps newer local text in conflict recovery.

**Change guidance:** keep `StudioPage` as the wiring layer and place a workflow’s request/state transitions in its focused hook. Update the hook tests when changing selection, draft, inspector, action, proposal, export, or project-loading behavior.

**Primary sources:** `frontend/src/features/studio/hooks/useStudioProject.ts`, `useActiveDocument.ts`, `useStudioInspectorState.ts`, `useStudioActions.ts`.

## Epic-era orchestration: whole-book loop, providers, and search

`StudioPage` delegates composition to `useStudioPageModel`, which wires the workspace hooks above plus the newer capabilities below and passes them to `StudioPageView`.

**Whole-book loop.** `useWholeBookLoop` (#318) is a frontend-driven state machine over the streaming proposal transport plus atomic acceptance: `idle` → `running(current,total)` → `done(generated,stoppedEarly)` | `failed(generated,failedChapterTitle,message)`. Per planned chapter it streams a `generate` proposal, auto-accepts it, refreshes the project and jobs, and notifies the active-editor cache. Chapters run strictly sequentially because each draft depends on the previous accept. Stop or a project switch aborts an in-flight proposal before it can land a job or usage event and prevents any later chapter from starting. If atomic acceptance already began, it may finish; the completed chapter is counted as preserved work. The plan is recomputed from persisted documents at every start, so resume begins at the first chapter without an `ai-accepted` revision. `StudioWholeBookControl` (`frontend/src/features/studio/components/StudioWholeBookControl.tsx`) renders the plan hint, a polite `role="status"` progress line ("chapter k / n"), a visible stop control while running, and the preserved-work outcome after a stop or failure. It is embedded in `StudioNavigator` on the manuscript surface.

**Streaming proposals.** The Copilot drafts through the SSE streaming endpoint (`POST .../ai-proposals/stream`) via the dedicated client in `frontend/src/app/proposalStream.ts`, which keeps credentials and the CSRF header identical to the synchronous client. Deltas accumulate into the proposal preview only (`streamingText`); the manuscript changes through explicit accept. Aborting the in-flight stream cancels the proposal server-side with nothing persisted.

**Providers and search.** `useStudioProviders` loads the provider list from the API and falls back to `DEFAULT_PROVIDER_OPTIONS` (`studioConstants.ts`) on failure or an empty response, keeping the UI usable offline. `useStudioSearch` owns the navigator search form state via a reducer (`search`, `isSearching`, `searchResults`) and calls the shared `api.search` endpoint, which parameterizes the query into the project search route. Both are wired through `useStudioPageModel` into `StudioNavigator`.

**Usage.** `StudioUsagePanel` consumes `GET /api/projects/:projectId/usage` through `frontend/src/app/api.ts`. `useProjectUsage` loads the aggregate lazily when the Usage tab first becomes active and exposes an explicit refresh action. Its state, request epoch, and cancellation signal are project-scoped, so a prior project's totals or error cannot publish into the current workbench.

**Primary sources:** `frontend/src/features/studio/hooks/useStudioPageModel.ts`, `useWholeBookLoop.ts`, `wholeBookPlan.ts`, `useStudioProposal.ts`, `useStudioProviders.ts`, `useStudioSearch.ts`; `frontend/src/app/proposalStream.ts`; `frontend/src/features/studio/components/StudioWholeBookControl.tsx`; `frontend/src/features/studio/StudioNavigator.tsx`.

The navigator groups chapter rows under one header per volume in reading order; chapters without a resolved volume link fall back to the first volume (`StudioNavigator.tsx`). Volume and beat semantics are documented in `openwiki/architecture/volumes-and-beats.md`; the streaming protocol and the stop/resume behavior of the loop in `openwiki/architecture/streaming-and-whole-book.md`.

## API client behavior

Studio code calls the shared `api` object in `frontend/src/app/api.ts`, rather than issuing component-level requests. JSON requests include cookies (`credentials: 'include'`). For `POST`, `PUT`, `PATCH`, and `DELETE`, the client reads the `novel_engine_csrf` cookie and sends it as `X-CSRF-Token` when present. Request calls combine an optional caller signal with an internal timeout signal. An abort becomes either `Request cancelled.` or `Request timed out. Please retry.`; a network `TypeError` becomes the local-service-unavailable message. Non-OK JSON responses become `HttpError` with status and the unified envelope's `code`, `message`, and `details`; 204 responses are passed to the supplied void parser.

Downloads use a separate timed fetch with credentials and return a `Blob`; they surface download-specific timeout and HTTP errors. The API surface includes document save/revision restore, AI proposal/acceptance, reviews, exports, and jobs, and parses successful JSON through runtime contract parsers.

**Change guidance:** preserve the client’s credential, CSRF, timeout, error-normalization, and contract-parsing behavior when adding endpoints. Do not bypass it from Studio components.

**Primary source:** `frontend/src/app/api.ts`.

## Drafts, revisions, proposals, and exports

`useDocumentDraft` keeps project-and-document-scoped content and title drafts plus the loaded revision ID. Changing either identity creates a new owner token; timers and completion publications from the previous owner cannot mutate the current draft or revision baseline. Editing marks the save state as `saving` and debounces a `saveDocument` request by 1.5 seconds. The save sends the current base revision ID; a successful response for the still-current owner replaces the project's saved document, advances the loaded revision ID, marks the draft `saved`, and refreshes revision history. A 409 `HttpError` becomes `conflict`; the hook refreshes the server project to obtain the latest document while retaining the local draft. The editor then exposes two explicit choices: **Load latest (discard local)** adopts the server content and revision, or **Keep local and retry overwrite** resubmits the local content against the latest revision. Other failures become `error` and remain readable through the shared error surface.

History restoration posts the requested revision together with the currently loaded base revision ID. On success for the still-current owner it installs the restored document, advances the revision ID, updates project state, and refreshes revisions. Owner changes abort the aggregate refresh used by conflict recovery; save, restore, and revision completions that cannot be cancelled are identity/version checked before they publish. The History panel describes restoration as creating a new revision while preserving the chain.

Copilot submits only `continue` or `rewrite` proposals for the active document using the project's selected provider (falling back to `mock`). The stream and its preview are owned by the current project/document pair and are aborted when that owner changes. The panel displays returned proposal Markdown as a preview. It does not change the manuscript until Accept. Once acceptance commits, a project-scoped reload reconciles the originating document even if the author selected another document; only the matching document owner may reset the active-editor cache. A project switch aborts the remaining reload and suppresses all publication into the new workbench.

Export first creates an export record, prepends it to local export history, downloads the returned URL as a blob, creates a temporary object URL, clicks a temporary download link named `<project title>.<extension>` (`markdown` uses `.md`), then revokes the URL shortly afterward. The dedicated Export panel offers Markdown, DOCX, and EPUB, retains recent results, and can show a retryable failure. History is revision-only.

Review, proposal generation/acceptance, export, settings save, retry, reorder, document creation, history restore, and job refresh expose pending state. Initiating controls use `disabled` and/or `aria-busy`, and hooks guard duplicate requests with in-flight refs. Only the exact initiator is announced busy; related controls may be disabled without adopting its accessible name. Failures remain readable until a retry succeeds. Commands remember the initiating element and the focus position at invocation, restore it only when the author has not deliberately moved focus, and use a stable workflow-local fallback if the initiator disappears. Whole-book progress and Stop stay outside the selected Inspector panel. Export treats create, catalog refresh, blob fetch, object URL, and synthetic click as one project owner: switching projects aborts remaining requests, prevents the old download, and revokes every object URL.

**Primary sources:** `frontend/src/features/studio/hooks/useDocumentDraft.ts`, `useRevisionCache.ts`, `useStudioProposal.ts`, `useExportDownload.ts`; `frontend/src/features/studio/components/StudioCopilotPanel.tsx`, `StudioHistoryPanel.tsx`, and `StudioTopbar.tsx`.

## Accessibility and responsive behavior

The save indicator in `StudioEditorPane` is an atomic, polite `status` for normal states (including saved and saving). Conflict and error become an assertive `alert`; these states show the failure icon, with error text rendered as `Save failed` and conflict rendered as `conflict`. The document title has an accessible label, and CodeMirror’s editable content has `aria-label="Markdown editor"` and `aria-multiline="true"`.

Outside settings, the Inspector has six ARIA tabs—Copilot, Review, History, Export, Jobs, and Usage—inside a labelled horizontal `tablist`. It uses the APG single-tab-stop pattern: the active tab has `tabIndex=0`, inactive tabs have `tabIndex=-1`, each tab has a generated ID, `aria-controls`, and `aria-selected`, and each associated `tabpanel` has `aria-labelledby` while inactive panels use `hidden`. ArrowRight/ArrowLeft wrap through tabs; Home and End select the first/last tab, navigate to its canonical URL, and move focus to it. The tablist uses a contained three-column by two-row layout with 44px minimum-height controls rather than a clipped fixed row. Settings intentionally renders no tablist.

The Markdown editor lazy-loads CodeMirror with Markdown language support, history/default keymaps, line wrapping, no gutters, and a system serif stack. The scrolling text is 19px with 1.8 line height; content is centered and limited to `72ch`. Its focused editor has a 3px teal outline. Responsive padding uses `clamp()`. Global visible-focus styling applies the same teal outline to buttons, form controls, and menu summaries.

At widths from 821px through 949px, Studio changes from its three-column desktop grid to an editor-first single column: top bar, editor, navigation, Inspector, and status bar. The same editor-first ordering is retained below 820px. Navigation and Inspector use native `details`/`summary` disclosures, and both summaries remain visible and keyboard-reachable across desktop and responsive transitions rather than appearing only after a breakpoint. The editor has a minimum 70vh height, responsive horizontal padding, a bounded reading width, and a visible CodeMirror focus boundary. Icon and reorder controls provide at least 44px by 44px targets; supported viewports avoid horizontal overflow.

The end-to-end workflow is the owning browser check for 1440, 1024, 949, 900, 800, and 375px widths, including route-specific Export/History surfaces, URL-backed click/keyboard/Back/Forward behavior, editor focus, no overlap among title/save/word-count controls, busy/disabled controls, conflict recovery, and reduced-motion behavior. A passing local run is evidence for that candidate only; hosted CI and human review remain separate evidence surfaces.

**Change guidance:** run the Studio component tests and the Playwright Studio workflow after modifying ARIA roles/live regions, layout grid rules, editor focus, or responsive sizing. Keep the assertions focused on the exposed behavior above.

**Primary sources:** `frontend/src/features/studio/StudioEditorPane.tsx`, `StudioInspector.tsx`, `MarkdownEditor.tsx`; `frontend/src/index.css`; `frontend/src/features/studio/StudioComponents.test.tsx`; `frontend/tests/e2e-ts/studio-ts.spec.ts`.
