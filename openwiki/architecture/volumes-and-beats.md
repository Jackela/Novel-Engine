# Volumes and beats

The manuscript structure is fixed at two levels: the project holds an ordered list of **volumes**, and every chapter belongs to exactly one volume (ADR-0005). Projects start with a single default volume — creation and legacy import included — so no chapter is ever unplaced. Independently of placement, each chapter may link to exactly one **beat**: a heading unit of the project's outline document that the chapter fulfills. Volume position and beat linkage are two separate dimensions and must not be conflated.

**Primary sources:** `docs/adr/0005-fixed-two-level-hierarchy.md`, `server/src/contexts/studio/application/volume_service.ts`, `server/src/contexts/studio/application/beat_association_service.ts`.

## Volumes and the in-volume position

Volume CRUD keeps the at-least-one-volume invariant: deleting the project's last volume is refused. Chapter placement moves a chapter to the tail of its target volume; non-chapter documents refuse placement. Volume order is a whole-set reorder — the request lists every project volume exactly once and positions become 1..n (`VolumeService.applyVolumeOrder`).

The UI-facing **in-volume sequence number is `document.position`**. New chapters get the next position inside their target volume: the maximum existing in-volume position plus one; chapters without a volume target and other document kinds position flat per kind (`server/src/contexts/studio/infrastructure/document_store_part.ts`, `nextPosition`). Chapter reorder stays a document-level channel (`PUT /api/projects/:projectId/documents/reorder`); volume order has its own routes (`server/src/contexts/studio/interface/http/volume_routes.ts`).

The Studio navigator renders chapters grouped under one header per volume in reading order; chapters without a resolved link fall back to the first volume (`frontend/src/features/studio/StudioNavigator.tsx`).

## Beat references are soft links by title

`beat_ref` stores the **heading title of an outline beat**, not a position or sequence number. Writing a link (`PUT /api/projects/:projectId/documents/:documentId/beat`) validates that the requested title exists in the current outline beats and refuses otherwise; clearing passes `null`. Only chapters may hold a beat reference (`server/src/contexts/studio/infrastructure/document_store_part.ts`, `setBeatReference`).

Every read resolves the stored title against the live outline. If the beat heading is later renamed or removed, the link **degrades to null instead of erroring** — the association is dangling-safe by design (`server/src/contexts/studio/application/beat_association_service.ts`, `linkedChapterBeat`). The beats themselves are split from the first outline-kind document's current revision markdown (`server/src/contexts/studio/application/outline_beats.ts`).

This semantics distinction matters for generation: `document.position` becomes `chapter_number` in job metadata and the deterministic provider's chapter draft, while the resolved beat rides into the prompt as part of the resident context (see `resident-context.md`). During a whole-book run the landing writes `chapter_number: document.position` (`server/src/contexts/studio/application/proposal_landing.ts`), never the beat reference.

**Primary sources:** `server/src/contexts/studio/application/volume_service.ts`, `server/src/contexts/studio/application/beat_association_service.ts`, `server/src/contexts/studio/application/outline_beats.ts`, `server/src/contexts/studio/infrastructure/document_store_part.ts`, `server/src/contexts/studio/interface/http/volume_routes.ts`, `frontend/src/features/studio/StudioNavigator.tsx`.
