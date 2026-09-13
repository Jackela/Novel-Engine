# Design: fixed authoring structure budgets

## Inventory (measured on baseline 76403763)

| Structure | Write paths | Bound before this change | Risk when unbounded |
| --- | --- | --- | --- |
| Documents per project | `POST /documents`, project seed, legacy import | none (1 MiB HTTP body only); legacy import caps at 2,000 chapters | unbounded shell projection rows, whole-set reorder cost, FTS growth |
| Volumes per project | `POST /volumes`, project seed | none | unbounded unpaginated volume list and whole-set volume reorder |
| Chapters per volume | chapter create (first-volume tail), `PUT .../volume` placement, import default volume, volume-deletion merge | none | unbounded in-volume tail scans and reading-order projection |
| Serialized Project settings JSON | `PUT /api/projects/:projectId` | free-form object, bounded only by the 1 MiB body | unbounded stored TEXT blob on the project row |
| Serialized document metadata JSON | document create/save | free-form object, bounded only by the 1 MiB body | unbounded stored TEXT copied into every immutable revision |
| Outline beats | outline document create/save/restore, proposal acceptance | derived from one document's markdown; only the implicit 1 MiB body ceiling (~10^5 minimal `## x` sections) | every beat read/link/generation resolution runs `findDocuments`, loading all project documents with current content, then splits the outline |
| Titles and names | all create/update routes | already 1–240 characters (Request validation constraints) | already bounded; unchanged |

Temporary hermetic probe (since deleted; raw-SQL seeding, hermetic SQLite,
`performance.now()` medians of single runs):

| Documents | Shell read | Shell JSON | Whole-set reorder | Reorder request body |
| --- | --- | --- | --- | --- |
| 101 | 1.3 ms | 38 KB | 6.3 ms | 2 KB |
| 1,001 | 3.8 ms | 378 KB | 48 ms | 21 KB |
| 5,001 | 13.8 ms | 1.9 MB | 159 ms | 109 KB |
| 25,001 | 86.6 ms | 9.6 MB | 766 ms | 564 KB |

| Beats in one outline | Outline markdown | Split time |
| --- | --- | --- |
| 1,000 | 27 KB | 0.7 ms |
| 5,000 | 135 KB | 1.1 ms |
| 20,000 | 540 KB | 4.2 ms |
| 100,000 | 2.7 MB | 20.7 ms |

Growth is linear, so the hazard is not algorithmic blowup but an unbounded
multiplier over whole-set surfaces. One hard functional cliff exists: each
reorder id costs 39 bytes of JSON, so the 1,048,576-byte body limit makes
whole-set reorder permanently inexpressible (413) above ~26,900 documents.
Structural capacity must stay far enough below that cliff for reorder to
remain a supported operation.

## Limits and their justification

| Resource | Limit | Justification |
| --- | --- | --- |
| `project_documents` | 2,500 | The largest admissible legacy import is 2,000 chapters in one project; 2,500 adds a 500-document outline/character/world/notes allowance on top (2.5x a generous 200-document story bible). Typical novel projects hold 30–150 documents, so the budget is 16–80x normal. It keeps reorder bodies at ~100 KB (under 10% of the body limit), shell JSON under ~1 MB, and sits 26x below the reorder cliff and 26x below the export source-document safety bound (65,536). |
| `project_volumes` | 100 | Real novels have 3–10 volumes; sprawling serials reach 20–50. 100 is a 2–10x margin over the extremes while keeping the unpaginated volume list, the whole-set volume reorder, and the reading-order projection trivially bounded. |
| `volume_chapters` | 2,000 | Legacy import lands every imported chapter in the single default volume, so the per-volume ceiling must be at least the import chapter ceiling (2,000) for existing imported projects to remain valid. 2,000 preserves exact parity: the largest import sits exactly at the inclusive bound. |
| `project_settings_bytes` | 16,384 | Settings are a configuration object (`{"provider":"mock"}` today, 20 bytes). 16,384 UTF-8 bytes is ~800x the default, matches the export manifest-bytes precedent for a small structured JSON budget, and stays 64x below the request-body limit. |
| `document_metadata_bytes` | 16,384 | The same free-form JSON seam on authoring structures; the legacy importer writes ~60 bytes (`legacy_filename`). The same budget keeps the two free-form JSON seams symmetric and bounds what every immutable revision copies. |
| `outline_beats` | 5,000 | An outline is one document, so its content per write is already implicitly capped by the 1 MiB body (~10^5 minimal sections). Real outlines hold at most ~1,000 beats (300 chapters x 3 sub-beats). 5,000 is a 5x margin that makes the implicit ceiling explicit at product scale and bounds the `findDocuments`-per-association scan multiplier. |

All limits are fixed and inclusive; no environment override may relax them
(the export/generation budget pattern). Values were chosen from the
measured growth table, the legacy import ceiling, and writing-studio
magnitudes — not from UI appearance.

## Error semantics

One domain error, `StructureCapacityExceededError(resource, limit,
observed)`, validates its inputs like the export/generation capacity errors
and saturates `observed` to at most `limit + 1`. HTTP maps it to 422
`STRUCTURE_CAPACITY_EXCEEDED`, message `Authoring structure capacity
exceeded.`, details `{resource, limit, observed}`. It is permanent for
unchanged input (removing structure is the remedy) and carries no retry
hint, unlike the 503 operation-capacity refusal whose resource frees
itself. The fixed message plus closed `resource` catalog keep the envelope
stable while the frontend continues rendering the envelope message through
its existing error channel.

## Enforcement placement (owning layers)

- Domain (`structure_capacity.ts`): the limit table, the closed resource
  enum, the error, and the serialized-scalar byte assertion. Domain stays
  import-free (`Buffer` is a Node global).
- Application: byte budgets are request-derived, so `ProjectService` and
  `DocumentService` validate `Buffer.byteLength(dumpJson(value))` before
  touching the store — no read-modify-write race exists for them.
- Infrastructure: count budgets are database-state-derived, so they are
  asserted inside the same SQLite write transaction that would insert —
  `addDocument` (project documents, volume chapters, outline beats),
  `addVolume` (project volumes), `placeDocumentInVolume` (volume chapters),
  `dropVolume` (the merged survivor's chapter count), and the shared
  revision-minting transaction (outline beats). SQLite's serialized writes
  make the check-then-insert atomic; two concurrent creations can never
  both pass one exhausted count. The beat check lives in the single
  chokepoint shared by author saves, restores, and proposal acceptance,
  so no content-minting path bypasses it. Counting uses bounded
  `limit + 1` projections (the export source-count query pattern), never
  materializing rows.
- Interface: one error-mapping branch and one capacity envelope schema
  shared by the affected routes; the OpenAPI baseline and generated
  frontend API types regenerate deliberately.

## Existing data

No migration and no stored-row revalidation. Reads, exports, generation,
and whole-set reorders of pre-limit structures are unaffected because none
of them mints new structure. The one deliberate edge: replaying a
pre-limit over-budget outline revision (restore) or accepting a proposal
that would push an outline past the beat budget mints a new revision, and
that new write is gated. Legacy import itself remains admissible because
its chapter ceiling equals the per-volume limit and sits below the
project limit.

## Options rejected

- Enforcing counts in the HTTP schema (`maxItems`): request shape cannot
  see database state, and reorder already requires the exact whole set.
- Application-layer count checks with a count port: a check outside the
  insert transaction admits a concurrent-create race; the store
  transaction is the only atomic seam.
- Truncating settings, metadata, or outline content to fit: silent canon
  mutation; the studio's precedent is loud permanent refusal.
- A separate persisted beat table to count beats: beats are derived state
  by design (#313); persisting them would create a second authority.
