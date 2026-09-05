# Tasks

## 1. Failure contract

- [x] 1.1 Add a regression test proving a missing `.env.local` remains optional.
- [x] 1.2 Add failing tests proving the same non-`ENOENT` read or parser error
      object escapes even when process overrides are available.
- [x] 1.3 Add cross-platform tests proving non-regular targets fail with one
      stable error while a symbolic link to a regular file remains valid.

## 2. Loader implementation

- [x] 2.1 Narrow metadata/read handling to `ENOENT` and rethrow every other
      actual filesystem error unchanged.
- [x] 2.2 Reject a resolved non-regular target before parsing.
- [x] 2.3 Parse only successfully read text outside the filesystem catch and
      preserve the existing process-override and default behavior.

## 3. Composition boundaries

- [x] 3.1 Prove `serve` configuration failure precedes its injected listener
      and leaves no database artifact from API build, migration, or recovery.
- [x] 3.2 Prove `backup` configuration failure precedes the injected ownership
      and backup boundaries.
- [x] 3.3 Prove `import` configuration failure precedes its injected runner.
- [x] 3.4 Prove `doctor` configuration failure leaves no database artifact from
      opening or inspection.

## 4. Validation and evidence

- [x] 4.1 Run focused tests and the owning server validation surfaces.
- [x] 4.2 Run strict OpenSpec and an independent closure review, then record
      fixed-SHA results and every skipped external gate.
