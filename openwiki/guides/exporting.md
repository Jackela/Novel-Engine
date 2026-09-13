# Exporting

Exports turn a project into a file you can keep, share, or publish. The
export always reflects the project's current **immutable snapshot** — the
exact revision set saved at that moment — so a re-export after more writing
never changes a file you already downloaded.

## Formats

Open the **Export** tab in the Inspector (or the Export section of the
project) and choose a format:

| Format | Good for |
|---|---|
| **Markdown** (`.md`) | Plain-text archival, version control, static site generators. |
| **DOCX** (`.docx`) | Word processors, editing with tracked changes, submission manuscripts. |
| **EPUB** (`.epub`) | E-readers and ebook stores. |

The file downloads through your browser under the project's title, for
example `My Novel.epub`, straight into your Downloads folder.

## Where copies are kept

Every export is also archived inside the studio's data directory (in the
`novel-engine-data` volume, under `exports/`), so past exports remain
available from the Export panel's history even if the original download never
reached your machine. The panel lists recent exports per format; a failed
export can be retried with one click.

Because the archive lives in the same volume as the database, it is covered
by the same [backup](backup-and-restore.md) routine.

## A safe publishing ritual

1. Finish and let the editor show **saved**.
2. Export Markdown — the lossless, future-proof copy of your words.
3. Store that file with your [backups](backup-and-restore.md), off the
   machine if you can.

Manuscripts are yours twice over: as the live database and as exported files
you control.
