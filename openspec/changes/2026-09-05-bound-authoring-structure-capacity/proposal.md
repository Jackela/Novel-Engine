# Bound authoring structure capacity

## Why

Downstream consumers of authoring structure are bounded (generation prompts
at 8 MiB, export sources at 65,536 documents, the catalog read at one
keyset page), but the structures themselves are not. Nothing stops a
project from accumulating unbounded documents and volumes, an unbounded
chapter count inside one volume, unbounded serialized Project settings and
document metadata JSON, or an unbounded beat count inside one outline
document. Every whole-set surface then scales with that unbounded count:
the structural shell projection, whole-set reorder validation, and the
per-association outline scan that loads every project document with its
current content. A project above roughly 26,900 documents can no longer
even express its mandatory whole-set reorder inside the 1 MiB request-body
limit.

## What Changes

- Bound each project's authoring structure with fixed inclusive limits:
  2,500 documents per project, 100 volumes per project, 2,000 chapters per
  volume, 16,384 UTF-8 bytes of serialized Project settings JSON, 16,384
  UTF-8 bytes of serialized document metadata JSON, and 5,000 outline beats
  accepted by any single outline-document write.
- Refuse a write that would exceed any limit before any row, revision,
  index, or project timestamp is written, with the stable permanent 422
  `STRUCTURE_CAPACITY_EXCEEDED` envelope whose details carry only the
  closed `resource` name, the inclusive `limit`, and an `observed` value
  saturated to at most `limit + 1`.
- Enforce count limits atomically inside the owning store write
  transactions (document creation, volume creation, chapter placement, and
  volume-deletion chapter merging), byte limits in the owning application
  services, and the beat limit at the single revision-minting chokepoint
  that author saves, restores, and proposal acceptance all share.
- Leave existing stored data untouched: no migration, no revalidation of
  stored rows, and reads/reorders of pre-limit structures keep working;
  only writes that would add new structure or grow a bounded scalar are
  gated.
- Document the 422 capacity envelope on the affected structure routes in
  the OpenAPI baseline and the shared error-code catalog; generated
  frontend API types stay synchronized, and the frontend keeps surfacing
  these refusals through the existing error-envelope message channel with
  no new UI.

## Impact

- Changes the studio domain capacity policy, the document/volume/project
  application services, the document and volume store write transactions,
  the revision-minting transaction, the studio error mapping, the shared
  error-code catalog, six structure route response contracts, the
  deliberate OpenAPI baseline, and generated frontend API types.
- Adds no dependency, environment variable, or database migration, and
  changes no successful payload. Legacy import stays admissible: its
  2,000-chapter ceiling lands exactly at the per-volume chapter limit and
  well below the per-project document limit.
- Projects that already exceed a limit keep reading, exporting,
  generating, and reordering; they only cannot grow the saturated
  structure further until the author removes some of it.

## Non-goals

- No pagination or projection change for structural reads; the bounded
  catalog page and split shell body are separate changes.
- No enforcement against generation-context, export, operation, or import
  capacity; those budgets remain their own policies.
- No configurable limits, per-kind document quotas, soft warnings, or
  automatic structure pruning; deleting structure is the only remedy.
- No truncation of stored settings, metadata, or outline content; refusal
  is permanent for unchanged input.

## Validation

- Contract tests red → green for every resource: above-limit 422 with the
  exact envelope, at-exact-limit success, and below-limit success, plus
  no-partial-write evidence (counts, rows, and revisions unchanged after
  refusal).
- Atomicity and chokepoint coverage: proposal acceptance and restore
  cannot mint outline content beyond the beat budget; concurrent-path
  count checks run inside the refused transaction.
- Full server suite and gates, frontend unit/type/lint/format/build with
  synchronized API types, strict OpenSpec validation, and fixed-SHA
  evidence.
