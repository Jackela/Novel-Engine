# Studio workspace

The Studio workspace is the project editor at `/projects/:projectId/:section?`. The optional section defaults to `manuscript`; section navigation also supports `outline`, `characters`, `world`, `review`, `history`, `export`, and `settings`. The root route is the entry page, `/projects` is the project library, and unknown routes return to the entry page. `StudioPage` is the composition point: it loads the project/session/reviews/exports, resolves the active document, and connects navigation, editor, Inspector, top bar, and status bar.

Route names and inspector surfaces are not one-to-one. The current mapping is:

| Route section | Primary surface | Behavior |
| --- | --- | --- |
| `manuscript`, `outline`, `characters`, `world` | Editor + selectable Inspector | The selected document is shown; the Inspector starts on Copilot unless the author selects another tab. |
| `review` | Review panel | Review is forced active and shows the latest snapshot-bound findings plus the run action. |
| `history` | History panel | Only immutable revision history and restore actions are shown. Export records are not mixed into this panel. |
| `export` | Export panel | Markdown, DOCX, and EPUB actions, pending/error state, and recent export links are shown. Export is not a History alias. |
| `settings` | Settings panel | Project settings render directly without the Inspector tablist. |

The top bar contains project identity and back navigation only. Review, Export, and Settings are route-driven and are not duplicated in a second top-bar menu.

**Primary sources:** `frontend/src/app/router.tsx`, `frontend/src/features/studio/StudioPage.tsx`.

## Workspace state and hooks

`useStudioProject(projectId)` loads the session, project, reviews, and exports concurrently. If that load fails, it navigates to `/` with `replace: true`. `useActiveDocument` selects an explicitly selected document when it fits the current outline/characters/world section; otherwise it selects the first document of that section. For other sections, it uses the selected document or the first document.

`useStudioInspectorState` derives the Inspector from route sections: `review`, `history`, `export`, and `settings` each select their own surface. Otherwise the selected Inspector starts as Copilot; selecting Jobs also loads its job list. `useStudioActions` owns document creation and reordering, review creation, project-settings updates, and job retry. `useStudioProposal`, `useExportDownload`, and `useStudioJobs` own their request state and guards. Workflow hooks report operational errors through the shared Inspector error area, while `useStudioProject` handles an aggregate-load failure by navigating to `/` with `replace: true`.

**Change guidance:** keep `StudioPage` as the wiring layer and place a workflow’s request/state transitions in its focused hook. Update the hook tests when changing selection, draft, inspector, action, proposal, export, or project-loading behavior.

**Primary sources:** `frontend/src/features/studio/hooks/useStudioProject.ts`, `useActiveDocument.ts`, `useStudioInspectorState.ts`, `useStudioActions.ts`.

## API client behavior

Studio code calls the shared `api` object in `frontend/src/app/api.ts`, rather than issuing component-level requests. JSON requests include cookies (`credentials: 'include'`). For `POST`, `PUT`, `PATCH`, and `DELETE`, the client reads the `novel_studio_csrf` cookie and sends it as `X-CSRF-Token` when present. Request calls combine an optional caller signal with an internal timeout signal. An abort becomes either `Request cancelled.` or `Request timed out. Please retry.`; a network `TypeError` becomes the local-service-unavailable message. Non-OK JSON responses become `HttpError` with status and available `detail`; 204 responses are passed to the supplied void parser.

Downloads use a separate timed fetch with credentials and return a `Blob`; they surface download-specific timeout and HTTP errors. The API surface includes document save/revision restore, AI proposal/acceptance, reviews, exports, and jobs, and parses successful JSON through runtime contract parsers.

**Change guidance:** preserve the client’s credential, CSRF, timeout, error-normalization, and contract-parsing behavior when adding endpoints. Do not bypass it from Studio components.

**Primary source:** `frontend/src/app/api.ts`.

## Drafts, revisions, proposals, and exports

`useDocumentDraft` keeps document-scoped content and title drafts plus the loaded revision ID. Editing marks the save state as `saving` and debounces a `saveDocument` request by 1.5 seconds. The save sends the current base revision ID; a successful response replaces the project’s saved document, advances the loaded revision ID, marks the draft `saved`, and refreshes revision history. A 409 `HttpError` becomes `conflict`; the hook refreshes the server project to obtain the latest document while retaining the local draft. The editor then exposes two explicit choices: **Load latest (discard local)** adopts the server content and revision, or **Keep local and retry overwrite** resubmits the local content against the latest revision. Other failures become `error` and remain readable through the shared error surface.

History restoration posts the requested revision together with the currently loaded base revision ID. On success it installs the restored document, advances the revision ID, updates project state, and refreshes revisions. The History panel describes this as creating a new revision while preserving the chain.

Copilot submits only `continue` or `rewrite` proposals for the active document using the project’s selected provider (falling back to `mock`). The panel displays returned proposal Markdown as a preview. It does not change the manuscript until Accept: acceptance is followed by a project reload, draft reset for the refreshed document, proposal clearing, and job refresh.

Export first creates an export record, prepends it to local export history, downloads the returned URL as a blob, creates a temporary object URL, clicks a temporary download link named `<project title>.<extension>` (`markdown` uses `.md`), then revokes the URL shortly afterward. The dedicated Export panel offers Markdown, DOCX, and EPUB, retains recent results, and can show a retryable failure. History is revision-only.

Review, proposal generation/acceptance, export, settings save, retry, reorder, document creation, and job refresh expose pending state. Initiating controls use `disabled` and/or `aria-busy`, and hooks guard duplicate requests with in-flight refs. Failures clear only when a subsequent operation succeeds; successful operations refresh the affected project, review, job, or export data. Settings and settings-like panels restore focus to the initiating control after completion. The proposal preview-before-accept and save conflict actions remain separate safeguards.

**Primary sources:** `frontend/src/features/studio/hooks/useDocumentDraft.ts`, `useRevisionCache.ts`, `useStudioProposal.ts`, `useExportDownload.ts`; `frontend/src/features/studio/components/StudioCopilotPanel.tsx`, `StudioHistoryPanel.tsx`, and `StudioTopbar.tsx`.

## Accessibility and responsive behavior

The save indicator in `StudioEditorPane` is an atomic, polite `status` for normal states (including saved and saving). Conflict and error become an assertive `alert`; these states show the failure icon, with error text rendered as `Save failed` and conflict rendered as `conflict`. The document title has an accessible label, and CodeMirror’s editable content has `aria-label="Markdown editor"` and `aria-multiline="true"`.

Outside settings, the Inspector has five ARIA tabs—Copilot, Review, History, Export, and Jobs—inside a labelled horizontal `tablist`. It uses the APG single-tab-stop pattern: the active tab has `tabIndex=0`, inactive tabs have `tabIndex=-1`, each tab has a generated ID, `aria-controls`, and `aria-selected`, and each associated `tabpanel` has `aria-labelledby` while inactive panels use `hidden`. ArrowRight/ArrowLeft wrap through tabs; Home and End select the first/last tab and move focus to it. Settings intentionally renders no tablist.

The Markdown editor lazy-loads CodeMirror with Markdown language support, history/default keymaps, line wrapping, no gutters, and a system serif stack. The scrolling text is 19px with 1.8 line height; content is centered and limited to `72ch`. Its focused editor has a 3px teal outline. Responsive padding uses `clamp()`. Global visible-focus styling applies the same teal outline to buttons, form controls, and menu summaries.

At widths from 821px through 949px, Studio changes from its three-column desktop grid to an editor-first single column: top bar, editor, collapsed navigation, collapsed Inspector, and status bar. The same editor-first ordering is retained below 820px. Navigation and Inspector disclosures expose their expanded state to assistive technology. The editor has a minimum 70vh height, responsive horizontal padding, a bounded reading width, and a visible CodeMirror focus boundary. Icon and reorder controls provide at least 44px by 44px targets; supported viewports avoid horizontal overflow.

The end-to-end workflow validates 1440, 1024, 949, 900, 800, and 375px widths, including route-specific Export/History surfaces, tab keyboard behavior, editor focus, no overlap among title/save/word-count controls, busy/disabled controls, conflict recovery, and reduced-motion behavior.

**Change guidance:** run the Studio component tests and the Playwright Studio workflow after modifying ARIA roles/live regions, layout grid rules, editor focus, or responsive sizing. Keep the assertions focused on the exposed behavior above.

**Primary sources:** `frontend/src/features/studio/StudioEditorPane.tsx`, `StudioInspector.tsx`, `MarkdownEditor.tsx`; `frontend/src/index.css`; `frontend/src/features/studio/StudioComponents.test.tsx`; `frontend/tests/e2e/studio.spec.ts`.
