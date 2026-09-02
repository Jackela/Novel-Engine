# Tasks

## 1. Failure contract

- [ ] 1.1 Add failing tests proving a missing `.env.local` remains optional.
- [ ] 1.2 Add failing tests proving the same non-`ENOENT` read or parser error
      object escapes even when process overrides are available.

## 2. Loader implementation

- [ ] 2.1 Narrow the file-read catch to `ENOENT` and rethrow every other error
      unchanged.
- [ ] 2.2 Parse only successfully read text outside the filesystem catch and
      preserve the existing process-override and default behavior.

## 3. Composition boundaries

- [ ] 3.1 Prove `serve` configuration failure precedes its injected listener
      and leaves no database artifact from API build, migration, or recovery.
- [ ] 3.2 Prove `backup` configuration failure precedes the injected ownership
      and backup boundaries.
- [ ] 3.3 Prove `import` configuration failure precedes its injected runner.
- [ ] 3.4 Prove `doctor` configuration failure leaves no database artifact from
      opening or inspection.

## 4. Validation and evidence

- [ ] 4.1 Run focused tests and the owning server validation surfaces.
- [ ] 4.2 Run strict OpenSpec and an independent closure review, then record
      fixed-SHA results and every skipped external gate.
